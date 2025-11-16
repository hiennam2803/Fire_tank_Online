import pymysql
import hashlib
import secrets
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import getpass
import os

class DatabaseManager:
    def __init__(self, host=None, user=None, password=None, database=None, port=None):
        # Sử dụng biến môi trường hoặc giá trị mặc định
        self.host = host or os.getenv('DB_HOST', 'localhost')
        self.user = user or os.getenv('DB_USER', 'root')
        self.password = password or os.getenv('DB_PASSWORD', 'Hien2832005@')
        self.database = database or os.getenv('DB_NAME', 'tank_battle')
        self.port = port or int(os.getenv('DB_PORT', '3306'))
        self.connection = None
        self.connect()

    def connect(self):
        """Kết nối đến MySQL database sử dụng PyMySQL"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                autocommit=True,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            print(" Đã kết nối đến MySQL database sử dụng PyMySQL")
            return True
            
        except pymysql.Error as e:
            print(f" Lỗi kết nối database: {e}")
            
            # Thử kết nối không cần database trước
            try:
                temp_conn = pymysql.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    port=self.port,
                    charset='utf8mb4'
                )
                print(" Kết nối MySQL thành công (không có database)")
                
                # Tạo database nếu chưa tồn tại
                with temp_conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
                    print(f" Đã tạo database: {self.database}")
                
                temp_conn.close()
                
                # Kết nối lại với database
                self.connection = pymysql.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    port=self.port,
                    autocommit=True,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor
                )
                print("Đã kết nối đến database")
                
                # Tạo tables
                self._create_tables()
                return True
                
            except pymysql.Error as e2:
                print(f" Vẫn lỗi: {e2}")
                return self._prompt_and_connect()

    def _prompt_and_connect(self):
        """Yêu cầu người dùng nhập thông tin và thử kết nối lại"""
        print("\n🔐 Vui lòng nhập thông tin MySQL:")
        self.host = input("Host (localhost): ").strip() or 'localhost'
        self.user = input("User (root): ").strip() or 'root'
        self.password = getpass.getpass("Password: ")
        self.database = input("Database (tank_battle): ").strip() or 'tank_battle'
        
        # Thử kết nối lại với thông tin mới
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                autocommit=True,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            print(" Kết nối thành công với thông tin mới!")
            
            # Tạo tables nếu cần
            self._create_tables()
            return True
        except pymysql.Error as e:
            print(f" Vẫn lỗi: {e}")
            return False

    def _create_tables(self):
        """Tạo các bảng cần thiết"""
        try:
            with self.connection.cursor() as cursor:
                # Tạo bảng players
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS players (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        games_played INT DEFAULT 0,
                        games_won INT DEFAULT 0,
                        total_damage_dealt INT DEFAULT 0,
                        total_shots_fired INT DEFAULT 0,
                        accuracy DECIMAL(5,2) DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        last_login TIMESTAMP NULL
                    )
                """)
                
                # Tạo bảng game_sessions
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS game_sessions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        session_code VARCHAR(10) UNIQUE NOT NULL,
                        map_id INT DEFAULT 1,
                        player1_id INT,
                        player2_id INT,
                        winner_id INT NULL,
                        duration_seconds INT DEFAULT 0,
                        player1_score INT DEFAULT 0,
                        player2_score INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (player1_id) REFERENCES players(id),
                        FOREIGN KEY (player2_id) REFERENCES players(id),
                        FOREIGN KEY (winner_id) REFERENCES players(id)
                    )
                """)
                
                # Tạo bảng player_stats
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS player_stats (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        player_id INT NOT NULL,
                        game_session_id INT NOT NULL,
                        final_hp INT DEFAULT 0,
                        damage_dealt INT DEFAULT 0,
                        shots_fired INT DEFAULT 0,
                        shots_hit INT DEFAULT 0,
                        reloads_count INT DEFAULT 0,
                        survival_time INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (player_id) REFERENCES players(id),
                        FOREIGN KEY (game_session_id) REFERENCES game_sessions(id)
                    )
                """)
                
                # Tạo indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_username ON players(username)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_sessions_created ON game_sessions(created_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_stats(player_id)")
                
            self.connection.commit()
            print(" Đã tạo các bảng thành công")
            
        except pymysql.Error as e:
            print(f" Lỗi tạo tables: {e}")

    def hash_password(self, password: str) -> str:
        """Hash mật khẩu với salt"""
        salt = secrets.token_hex(16)
        return f"{salt}${hashlib.sha256((salt + password).encode()).hexdigest()}"

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Xác thực mật khẩu"""
        try:
            salt, hash_value = hashed_password.split('$')
            return hashlib.sha256((salt + password).encode()).hexdigest() == hash_value
        except:
            return False

    def register_player(self, username: str, password: str, name: str = None) -> Tuple[bool, str]:
        """Đăng ký người chơi mới"""
        if not self.connection:
            return False, "Database connection failed"

        try:
            with self.connection.cursor() as cursor:
                # Kiểm tra username đã tồn tại chưa
                cursor.execute("SELECT id FROM players WHERE username = %s", (username,))
                if cursor.fetchone():
                    return False, "Username already exists"

                # Hash password và tạo player
                password_hash = self.hash_password(password)
                display_name = name if name else username
                
                cursor.execute(
                    "INSERT INTO players (username, name, password_hash) VALUES (%s, %s, %s)",
                    (username, display_name, password_hash)
                )
                
            self.connection.commit()
            return True, "Player registered successfully"
            
        except pymysql.Error as e:
            return False, f"Registration error: {e}"

    def authenticate_player(self, username: str, password: str) -> Tuple[bool, Optional[int], str]:
        """Xác thực người chơi"""
        if not self.connection:
            return False, None, "Database connection failed"

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, password_hash FROM players WHERE username = %s", 
                    (username,)
                )
                player = cursor.fetchone()

            if not player:
                return False, None, "Player not found"

            if self.verify_password(password, player['password_hash']):
                # Cập nhật last_login
                with self.connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE players SET last_login = %s WHERE id = %s",
                        (datetime.now(), player['id'])
                    )
                self.connection.commit()
                return True, player['id'], "Authentication successful"
            else:
                return False, None, "Invalid password"

        except pymysql.Error as e:
            return False, None, f"Authentication error: {e}"

    def create_game_session(self, player1_id: int, player2_id: int, map_id: int = 1) -> Optional[int]:
        """Tạo session game mới"""
        if not self.connection:
            return None

        try:
            with self.connection.cursor() as cursor:
                session_code = secrets.token_hex(5).upper()[:10]
                
                cursor.execute(
                    """INSERT INTO game_sessions 
                       (session_code, player1_id, player2_id, map_id) 
                       VALUES (%s, %s, %s, %s)""",
                    (session_code, player1_id, player2_id, map_id)
                )
                
                session_id = cursor.lastrowid
                return session_id
                
        except pymysql.Error as e:
            print(f"Error creating game session: {e}")
            return None

    def update_game_result(self, session_id: int, winner_id: Optional[int], 
                          duration: int, player1_score: int, player2_score: int):
        """Cập nhật kết quả game"""
        if not self.connection:
            return

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE game_sessions 
                       SET winner_id = %s, duration_seconds = %s, 
                           player1_score = %s, player2_score = %s 
                       WHERE id = %s""",
                    (winner_id, duration, player1_score, player2_score, session_id)
                )
            self.connection.commit()
        except pymysql.Error as e:
            print(f"Error updating game result: {e}")

    def update_player_stats(self, session_id: int, player_id: int, 
                           final_hp: int, damage_dealt: int, 
                           shots_fired: int, shots_hit: int, 
                           reloads_count: int, survival_time: int):
        """Cập nhật thống kê người chơi cho session"""
        if not self.connection:
            return

        try:
            with self.connection.cursor() as cursor:
                # Thêm stats cho session
                cursor.execute(
                    """INSERT INTO player_stats 
                       (player_id, game_session_id, final_hp, damage_dealt, 
                        shots_fired, shots_hit, reloads_count, survival_time) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (player_id, session_id, final_hp, damage_dealt, 
                     shots_fired, shots_hit, reloads_count, survival_time)
                )
                
                # Cập nhật tổng stats của player
                cursor.execute(
                    """UPDATE players 
                       SET games_played = games_played + 1,
                           total_damage_dealt = total_damage_dealt + %s,
                           total_shots_fired = total_shots_fired + %s
                       WHERE id = %s""",
                    (damage_dealt, shots_fired, player_id)
                )
                
            self.connection.commit()
            
        except pymysql.Error as e:
            print(f"Error updating player stats: {e}")

    def get_player_profile(self, player_id: int) -> Optional[Dict]:
        """Lấy thông tin profile người chơi"""
        if not self.connection:
            return None

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """SELECT id, username, name, games_played, games_won, 
                              total_damage_dealt, total_shots_fired, accuracy,
                              created_at, last_login
                       FROM players WHERE id = %s""",
                    (player_id,)
                )
                profile = cursor.fetchone()
                return profile
        except pymysql.Error as e:
            print(f"Error getting player profile: {e}")
            return None

    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Lấy bảng xếp hạng"""
        if not self.connection:
            return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """SELECT username, name, games_played, games_won, 
                              accuracy, total_damage_dealt
                       FROM players 
                       WHERE games_played > 0 
                       ORDER BY games_won DESC, accuracy DESC 
                       LIMIT %s""",
                    (limit,)
                )
                leaderboard = cursor.fetchall()
                return leaderboard
        except pymysql.Error as e:
            print(f"Error getting leaderboard: {e}")
            return []

    def close(self):
        """Đóng kết nối database"""
        if self.connection and self.connection.open:
            self.connection.close()
            print(" Đã đóng kết nối database")