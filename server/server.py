import socket
import threading
import json
import time
from server.game import GameEngine
from server.database_manager_pymysql import DatabaseManager
from common.messages import MessageTypes, GameConstants

class TankServer:
    def __init__(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host = '0.0.0.0'
        self.tcp_port = GameConstants.TCP_PORT
        self.udp_port = GameConstants.UDP_PORT
        self.game_engine = GameEngine()
        self.database = DatabaseManager()
        self.running = True
        self.player_authenticated = {}
        self.game_sessions = {}
        
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.udp_socket.bind((self.host, self.udp_port))
        self.tcp_socket.listen(GameConstants.MAX_PLAYERS)
        
        print(f"Server started on {self.host}:{self.tcp_port} (TCP) and {self.host}:{self.udp_port} (UDP)")

    def handle_tcp_client(self, client_socket, address):
        """Xử lý kết nối TCP từ client với xác thực"""
        player_id = None
        try:
            auth_data = client_socket.recv(1024).decode()
            print(f" Received auth data: {auth_data}")
            
            auth_info = json.loads(auth_data)
            
            auth_type = auth_info.get('type')
            username = auth_info.get('username', '')
            password = auth_info.get('password', '')
            
            player_db_id = None
            auth_success = False
            message = ""
            
            if auth_type == 'register':
                name = auth_info.get('name', username)
                success, message = self.database.register_player(username, password, name)
                if success:
                    auth_success, player_db_id, message = self.database.authenticate_player(username, password)
                else:
                    response = json.dumps({'type': 'auth_response','success': False,'message': message})
                    client_socket.send(response.encode())
                    client_socket.close()
                    return
                    
            elif auth_type == 'login':
                auth_success, player_db_id, message = self.database.authenticate_player(username, password)
            
            if auth_success and player_db_id:
                response = json.dumps({
                    'type': 'auth_response',
                    'success': True,
                    'player_id': player_db_id,
                    'message': 'Authentication successful'
                })
                client_socket.send(response.encode())
                
                player_id = str(player_db_id)
                print(f"Player {player_id} ({username}) connected from {address}")
                
                data = client_socket.recv(1024).decode()
                print(f" Received UDP port data: {data}")

                if data.startswith("UDP_PORT:"):
                    udp_port = int(data.split(":")[1])
                    # Thêm player vào game, truyền cả username
                    self.game_engine.add_player(player_id, (address[0], udp_port), client_socket, username)

                    self.player_authenticated[player_id] = {
                        'db_id': player_db_id,
                        'username': username
                    }
                    print(f" Player {player_id} UDP port registered: {udp_port}")
                    
                    client_socket.send(MessageTypes.WAITING_FOR_PLAYERS.encode())

                    while self.running:
                        try:
                            raw = client_socket.recv(1024)
                        except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                            print(f"⚠️ Lỗi TCP recv từ {address}: {e}")
                            break

                        if not raw:
                            print(f"🔌 Kết nối TCP đã đóng bởi client {address}")
                            break

                        try:
                            data = raw.decode()
                        except UnicodeDecodeError:
                            print(f"⚠️ Không thể decode dữ liệu TCP từ {address}, bỏ qua")
                            continue

                        if data == MessageTypes.READY:
                            self.game_engine.set_player_ready(player_id)
                            print(f"Player {player_id} is ready")
                            if self.game_engine.check_game_start():
                                self.start_game()

                        elif data == MessageTypes.RESTART:
                            print(f"Player {player_id} requested restart")
                            if self.game_engine.handle_restart_request(player_id):
                                self.restart_game() # Gửi RESTART cho cả 2
                            else:
                                # === SỬA LỖI: Gửi RESTART_ACCEPTED ===
                                # Gửi lại cho client vừa bấm T để họ biết là đang chờ
                                client_socket.send(MessageTypes.RESTART_ACCEPTED.encode())

                        elif data == 'RELOAD':
                            print(f"Player {player_id} requested reload via TCP fallback")
                            try:
                                self.game_engine.process_player_message(player_id, {'reload': True})
                            except Exception as e:
                                print(f"Error processing TCP reload for {player_id}: {e}")
                else:
                    print(f"Error: Client {player_id} không gửi UDP port. Đóng kết nối.")
                    
        except json.JSONDecodeError as e:
            print(f" JSON decode error: {e}")
            error_response = json.dumps({'type': 'auth_response','success': False,'message': 'Invalid authentication data'})
            try:
                client_socket.send(error_response.encode())
            except Exception:
                pass
        except Exception as e:
            print(f" Error with player: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if player_id:
                print(f"Disconnecting player {player_id}...")
                self.game_engine.remove_player(player_id)
                if player_id in self.player_authenticated:
                    del self.player_authenticated[player_id]
            client_socket.close()
            print(f"Connection from {address} closed.")


    def start_game(self):
        """Bắt đầu game mới với tracking session"""
        print("Attempting to start game...")
        players = list(self.game_engine.players.keys())
        if len(players) == 2:
            if players[0] not in self.player_authenticated or players[1] not in self.player_authenticated:
                print("LỖI: Không thể bắt đầu game. Thiếu thông tin xác thực của player.")
                return

            player1_db_id = self.player_authenticated[players[0]]['db_id']
            player2_db_id = self.player_authenticated[players[1]]['db_id']
            
            # Cập nhật tên trong game engine
            self.game_engine.update_player_name(players[0], self.player_authenticated[players[0]]['username'])
            self.game_engine.update_player_name(players[1], self.player_authenticated[players[1]]['username'])
            
            session_id = self.database.create_game_session(
                player1_db_id, player2_db_id, self.game_engine.current_map
            )
            self.game_engine.current_session_id = session_id
        
        self.game_engine.start_game()
        print("Starting game with 2 players!")
        
        for socket in self.game_engine.get_all_tcp_sockets():
            try:
                socket.send(MessageTypes.GAME_START.encode())
            except Exception as e:
                print(f"Lỗi khi gửi GAME_START: {e}")

    def _end_game(self, winner_id):
        """Kết thúc game và lưu stats (được gọi bởi game_engine)"""
        
        # Đảm bảo hàm này được gọi từ bên trong game_engine update
        # (Nó sẽ được gọi khi HP <= 0)
        
        # Chỉ lưu stats nếu game đã thực sự bắt đầu
        if not self.game_engine.game_start_time:
            print("Game kết thúc trước khi timer bắt đầu. Bỏ qua lưu stats.")
            return

        duration = int(time.time() - self.game_engine.game_start_time)
        
        if hasattr(self.game_engine, 'current_session_id') and self.game_engine.current_session_id:
            winner_db_id = None
            if winner_id and winner_id in self.player_authenticated:
                winner_db_id = self.player_authenticated[winner_id]['db_id']
            
            print(f"Lưu kết quả: session={self.game_engine.current_session_id}, winner={winner_db_id}")
            
            self.database.update_game_result(
                self.game_engine.current_session_id,
                winner_db_id,
                duration,
                self.game_engine.get_player_score(winner_id) if winner_id else 0,
                self.game_engine.get_player_score(self.get_opponent_id(winner_id)) if winner_id else 0
            )
            
            # Lưu stats cho từng player
            # Lấy danh sách player ID từ self.player_authenticated để đảm bảo an toàn
            for player_id in list(self.player_authenticated.keys()):
                if player_id in self.game_engine.players or self.game_engine.game_state['game_over']:
                    db_id = self.player_authenticated[player_id]['db_id']
                    stats = self.game_engine.get_player_stats(player_id)
                    
                    if stats: # Chỉ lưu nếu có stats
                        self.database.update_player_stats(
                            self.game_engine.current_session_id,
                            db_id,
                            stats['final_hp'],
                            stats['damage_dealt'],
                            stats['shots_fired'],
                            stats['shots_hit'],
                            stats['reloads_count'],
                            stats['survival_time']
                        )
                        
                        if winner_id == player_id:
                            try:
                                if not self.database.connection:
                                    self.database.connect() 
                                
                                with self.database.connection.cursor() as cursor:
                                    cursor.execute(
                                        "UPDATE players SET games_won = games_won + 1 WHERE id = %s",
                                        (db_id,)
                                    )
                                self.database.connection.commit()
                            except Exception as e:
                                print(f"Lỗi cập nhật CSDL: {e}")
        
        # Logic _end_game gốc của GameEngine đã được gọi bên trong nó

    def get_opponent_id(self, player_id):
        """Lấy ID của đối thủ"""
        players = list(self.game_engine.players.keys())
        if not player_id or not players or len(players) < 2:
             return None
        return players[1] if str(players[0]) == str(player_id) else players[0]

    def handle_udp_data(self):
        """Xử lý dữ liệu UDP từ clients"""
        while self.running:
            try:
                data, address = self.udp_socket.recvfrom(1024)
                message = json.loads(data.decode())
                player_id = message.get('id')
                
                if player_id in self.game_engine.players:
                    # Cập nhật địa chỉ UDP (phòng khi bị thay đổi)
                    self.game_engine.players[player_id]['udp_address'] = address
                    
                    if self.game_engine.game_started:
                        self.game_engine.process_player_message(player_id, message)
                    
            except Exception as e:
                pass

    def broadcast_game_state(self):
        """Gửi game state tới tất cả players"""
        if not self.game_engine.players:
            return
            
        # Yêu cầu game_engine build state mới nhất
        game_state = self.game_engine.get_game_state()
        
        # Kiểm tra nếu game vừa kết thúc, gọi _end_game để lưu stats
        if game_state['game_over'] and self.game_engine.game_started:
            # game_started flag vẫn là True, nghĩa là _end_game chưa được gọi
            self._end_game(game_state['winner_id'])
            # GameEngine sẽ set game_started = False
            
        
        game_data = json.dumps(game_state).encode()
        
        for player_id in list(self.game_engine.players.keys()):
            udp_address = self.game_engine.get_player_udp_address(player_id)
            if udp_address:
                try:
                    self.udp_socket.sendto(game_data, udp_address)
                except Exception as e:
                    print(f"Lỗi broadcast UDP: {e}")

    def restart_game(self):
        """Khởi động lại game"""
        print("Restarting game...")
        self.game_engine.restart_game()
        
        # Gửi tín hiệu restart cho tất cả players
        for socket in self.game_engine.get_all_tcp_sockets():
            try:
                socket.send(MessageTypes.RESTART.encode())
            except:
                pass
        
        print("Game reset complete, waiting for players to ready up...")

    def update_game_loop(self):
        """Vòng lặp cập nhật game chính"""
        while self.running:
            try:
                self.game_engine.update_game()
                self.broadcast_game_state()
                time.sleep(1/60)  # 60 FPS
            except Exception as e:
                print(f"Lỗi trong game loop: {e}")
                import traceback
                traceback.print_exc()


    def accept_tcp_connections(self):
        """Chấp nhận kết nối TCP mới"""
        while self.running:
            try:
                client_socket, address = self.tcp_socket.accept()
                if len(self.game_engine.players) < GameConstants.MAX_PLAYERS:
                    threading.Thread(
                        target=self.handle_tcp_client,
                        args=(client_socket, address),
                        daemon=True
                    ).start()
                else:
                    client_socket.send(MessageTypes.SERVER_FULL.encode())
                    client_socket.close()
            except Exception as e:
                if self.running:
                    print(f"TCP accept error: {e}")

    def start(self):
        """Khởi động server"""
        threading.Thread(target=self.accept_tcp_connections, daemon=True).start()
        threading.Thread(target=self.handle_udp_data, daemon=True).start()
        threading.Thread(target=self.update_game_loop, daemon=True).start()
        
        print("Server is running...")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down server...")
            self.running = False
            self.tcp_socket.close()
            self.udp_socket.close()
            self.database.close()

if __name__ == "__main__":
    server = TankServer()
    server.start()