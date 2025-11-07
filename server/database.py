# server/database.py
import mysql.connector
from mysql.connector import Error
import hashlib
import time

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        """Kết nối đến MySQL database - HÃY CHỈNH SỬA THÔNG SỐ NÀY THEO MÁY BẠN"""
        try:
            self.connection = mysql.connector.connect(
                host='localhost',          # Địa chỉ MySQL server
                user='root',               # Tên đăng nhập MySQL
                password='',               # Mật khẩu MySQL (để trống nếu không có)
                database='tank_game',      # Tên database
                autocommit=True,
                port=3306                  # Port MySQL (mặc định: 3306)
            )
            if self.connection.is_connected():
                print("✅ Kết nối MySQL thành công")
                return True
        except Error as e:
            print(f"❌ Lỗi kết nối MySQL: {e}")
            print("📋 Hãy kiểm tra:")
            print("   - MySQL đã được cài đặt và chạy chưa?")
            print("   - Database 'tank_game' đã được tạo chưa?")
            print("   - Thông tin đăng nhập MySQL có đúng không?")
            return False

    def hash_password(self, password):
        """Mã hóa mật khẩu"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password):
        """Đăng ký user mới"""
        try:
            cursor = self.connection.cursor()
            
            # Kiểm tra username đã tồn tại chưa
            check_query = "SELECT id FROM users WHERE username = %s"
            cursor.execute(check_query, (username,))
            if cursor.fetchone():
                return False, "Tên đăng nhập đã tồn tại"
            
            # Thêm user mới
            hashed_password = self.hash_password(password)
            insert_query = """
                INSERT INTO users (username, password, created_at) 
                VALUES (%s, %s, NOW())
            """
            cursor.execute(insert_query, (username, hashed_password))
            return True, "Đăng ký thành công"
            
        except Error as e:
            return False, f"Lỗi database: {e}"
        finally:
            if cursor:
                cursor.close()

    def login_user(self, username, password):
        """Xác thực đăng nhập"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            hashed_password = self.hash_password(password)
            
            query = """
                SELECT id, username, games_played, wins 
                FROM users 
                WHERE username = %s AND password = %s
            """
            cursor.execute(query, (username, hashed_password))
            user = cursor.fetchone()
            
            if user:
                # Cập nhật last_login
                update_query = "UPDATE users SET last_login = NOW() WHERE id = %s"
                cursor.execute(update_query, (user['id'],))
                return True, "Đăng nhập thành công", user
            else:
                return False, "Tên đăng nhập hoặc mật khẩu không đúng", None
                
        except Error as e:
            return False, f"Lỗi database: {e}", None
        finally:
            if cursor:
                cursor.close()

    def update_user_stats(self, user_id, won=False):
        """Cập nhật thống kê người chơi"""
        try:
            cursor = self.connection.cursor()
            if won:
                query = "UPDATE users SET games_played = games_played + 1, wins = wins + 1 WHERE id = %s"
            else:
                query = "UPDATE users SET games_played = games_played + 1 WHERE id = %s"
            cursor.execute(query, (user_id,))
            return True
        except Error as e:
            print(f"Lỗi cập nhật stats: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def close(self):
        """Đóng kết nối database"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("✅ Đã đóng kết nối MySQL")