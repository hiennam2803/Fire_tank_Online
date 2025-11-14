import socket
import threading
import json
import time
from server.game import GameEngine
from server.database_manager_pymysql import DatabaseManager  # Đổi import này
from common.messages import MessageTypes, GameConstants

class TankServer:
    def __init__(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host = '0.0.0.0'
        self.tcp_port = GameConstants.TCP_PORT
        self.udp_port = GameConstants.UDP_PORT
        self.game_engine = GameEngine()
        self.database = DatabaseManager()  # Sẽ sử dụng PyMySQL
        self.running = True
        self.player_authenticated = {}
        self.game_sessions = {}
        
    # Gán (bind) các socket
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.udp_socket.bind((self.host, self.udp_port))
        self.tcp_socket.listen(GameConstants.MAX_PLAYERS)
        
        print(f"Server started on {self.host}:{self.tcp_port} (TCP) and {self.host}:{self.udp_port} (UDP)")

    def handle_tcp_client(self, client_socket, address):
        """Xử lý kết nối TCP từ client với xác thực"""
        player_id = None
        try:
            # Nhận thông tin đăng nhập từ client
            auth_data = client_socket.recv(1024).decode()
            print(f" Received auth data: {auth_data}")  # Gỡ lỗi
            
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
                    # Tự động đăng nhập sau khi đăng ký
                    auth_success, player_db_id, message = self.database.authenticate_player(username, password)
                else:
                    response = json.dumps({
                        'type': 'auth_response',
                        'success': False,
                        'message': message
                    })
                    client_socket.send(response.encode())
                    client_socket.close()
                    return
                    
            elif auth_type == 'login':
                auth_success, player_db_id, message = self.database.authenticate_player(username, password)
            
            # Gửi phản hồi xác thực
            if auth_success and player_db_id:
                response = json.dumps({
                    'type': 'auth_response',
                    'success': True,
                    'player_id': player_db_id,
                    'message': 'Authentication successful'
                })
                client_socket.send(response.encode())
                
                # Tiếp tục quy trình kết nối bình thường
                player_id = str(player_db_id)
                print(f"Player {player_id} ({username}) connected from {address}")
                
                # Nhận UDP port từ client
                #  Gửi phản hồi xác thực
                client_socket.send(response.encode())

                player_id = str(player_db_id)
                print(f"Player {player_id} ({username}) connected from {address}")

                #  Gửi player_id NGAY LẬP TỨC (client đang chờ cái này)
                client_socket.send(player_id.encode())

                #  Gửi trạng thái WAITING ngay sau player_id
                client_socket.send(MessageTypes.WAITING_FOR_PLAYERS.encode())

                #  Sau đó mới nhận UDP_PORT từ client
                data = client_socket.recv(1024).decode()
                print(f" Received UDP port: {data}")

                if data.startswith("UDP_PORT:"):
                    udp_port = int(data.split(":")[1])
                    self.game_engine.add_player(player_id, (address[0], udp_port), client_socket)

                    self.player_authenticated[player_id] = {
                        'db_id': player_db_id,
                        'username': username
                    }

                    print(f" Player {player_id} UDP port registered: {udp_port}")

                
                # Vòng lặp chính xử lý client TCP
                while self.running:
                    try:
                        raw = client_socket.recv(1024)
                    except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                        # Thông báo lỗi nhận TCP (ví dụ WinError 10053) và dọn dẹp kết nối an toàn
                        print(f"⚠️ Lỗi TCP recv từ {address}: {e}")
                        break

                    # Nếu client đóng kết nối, recv trả về b''
                    if not raw:
                        print(f"🔌 Kết nối TCP đã đóng bởi client {address}")
                        break

                    try:
                        data = raw.decode()
                    except UnicodeDecodeError:
                        # Nếu không decode được, bỏ qua bản tin này
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
                            self.restart_game()
                        else:
                            client_socket.send(MessageTypes.RESTART_ACCEPTED.encode())

                    elif data == 'RELOAD':
                        # Chuỗi TCP thuần cung cấp fallback cho lệnh nạp đạn (client có thể gửi ngoài UDP)
                        print(f"Player {player_id} requested reload via TCP fallback")
                        try:
                            self.game_engine.process_player_message(player_id, {'reload': True})
                        except Exception as e:
                            print(f"Error processing TCP reload for {player_id}: {e}")
                        
        except json.JSONDecodeError as e:
            print(f" JSON decode error: {e}")
            error_response = json.dumps({
                'type': 'auth_response',
                'success': False,
                'message': 'Invalid authentication data'
            })
            client_socket.send(error_response.encode())
            client_socket.close()
        except Exception as e:
            print(f" Error with player: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if player_id:
                self.game_engine.remove_player(player_id)
                if player_id in self.player_authenticated:
                    del self.player_authenticated[player_id]
            client_socket.close()


    def start_game(self):
        """Bắt đầu game mới với tracking session"""
        # Tạo session trong database
        players = list(self.game_engine.players.keys())
        if len(players) == 2:
            player1_db_id = self.player_authenticated[players[0]]['db_id']
            player2_db_id = self.player_authenticated[players[1]]['db_id']
            
            session_id = self.database.create_game_session(
                player1_db_id, player2_db_id, self.game_engine.current_map
            )
            self.game_engine.current_session_id = session_id
            self.game_engine.game_start_time = time.time()
        
        self.game_engine.start_game()
        print("Starting game with 2 players!")
        
        # Gửi tín hiệu bắt đầu game cho tất cả players
        for socket in self.game_engine.get_all_tcp_sockets():
            try:
                socket.send(MessageTypes.GAME_START.encode())
            except:
                pass

    def _end_game(self, winner_id):
        """Kết thúc game và lưu stats"""
        # Tính thời gian game
        duration = int(time.time() - self.game_engine.game_start_time)
        
        # Lưu kết quả game
        if hasattr(self.game_engine, 'current_session_id') and self.game_engine.current_session_id:
            winner_db_id = None
            if winner_id and winner_id in self.player_authenticated:
                winner_db_id = self.player_authenticated[winner_id]['db_id']
            
            # Cập nhật kết quả game session
            self.database.update_game_result(
                self.game_engine.current_session_id,
                winner_db_id,
                duration,
                self.game_engine.get_player_score(winner_id) if winner_id else 0,
                self.game_engine.get_player_score(self.get_opponent_id(winner_id)) if winner_id else 0
            )
            
            # Lưu stats cho từng player
            for player_id, player_data in self.game_engine.players.items():
                if player_id in self.player_authenticated:
                    db_id = self.player_authenticated[player_id]['db_id']
                    stats = self.game_engine.get_player_stats(player_id)
                    
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
                    
                    # Cập nhật số trận thắng
                    if winner_id == player_id:
                        self.database.connection.cursor().execute(
                            "UPDATE players SET games_won = games_won + 1 WHERE id = %s",
                            (db_id,)
                        )
                        self.database.connection.commit()
        
        # Gọi hàm gốc
        self.game_engine._end_game(winner_id)

    def get_opponent_id(self, player_id):
        """Lấy ID của đối thủ"""
        players = list(self.game_engine.players.keys())
        return players[1] if players[0] == player_id else players[0]

    # Các phương thức khác giữ nguyên...
    def handle_udp_data(self):
        """Xử lý dữ liệu UDP từ clients"""
        while self.running:
            try:
                data, address = self.udp_socket.recvfrom(1024)
                message = json.loads(data.decode())
                player_id = message.get('id')
                
                if player_id in self.game_engine.players and self.game_engine.game_started:
                    self.game_engine.process_player_message(player_id, message)
                    
            except Exception as e:
                print(f"UDP error: {e}")

    def broadcast_game_state(self):
        """Gửi game state tới tất cả players"""
        game_data = json.dumps(self.game_engine.get_game_state()).encode()
        for player_id in self.game_engine.players:
            udp_address = self.game_engine.get_player_udp_address(player_id)
            if udp_address:
                try:
                    self.udp_socket.sendto(game_data, udp_address)
                except:
                    pass

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
            self.game_engine.update_game()
            self.broadcast_game_state()
            time.sleep(1/60)  # 60 FPS

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
                print(f"TCP accept error: {e}")

    def start(self):
        """Khởi động server"""
        # Bắt đầu các threads
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
