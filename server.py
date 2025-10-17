# server.py
import socket
import threading
import json
import time
import math

class TankServer:
    def __init__(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.host = 'localhost'
        self.host = '0.0.0.0'
        self.tcp_port = 5555
        self.udp_port = 5556
        
        self.players = {}
        self.bullets = []
        self.game_state = {'players': {}, 'bullets': [], 'game_over': False}
        self.ready_players = set()
        self.restart_requests = set()
        self.game_started = False
        self.running = True
        
        # Bind sockets
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.udp_socket.bind((self.host, self.udp_port))
        
        self.tcp_socket.listen(2)
        print(f"Server started on {self.host}:{self.tcp_port} (TCP) and {self.host}:{self.udp_port} (UDP)")

    def handle_tcp_client(self, client_socket, address):
        """Xử lý kết nối TCP từ client"""
        player_id = str(len(self.players) + 1)
        print(f"Player {player_id} connected from {address}")
        
        # Gửi ID cho client
        client_socket.send(player_id.encode())
        
        try:
            # Nhận UDP port từ client
            data = client_socket.recv(1024).decode()
            if data.startswith("UDP_PORT:"):
                udp_port = int(data.split(":")[1])
                self.players[player_id] = {
                    'tcp_socket': client_socket,
                    'udp_address': (address[0], udp_port),
                    'x': 100 if player_id == '1' else 700,
                    'y': 300,
                    'angle': 0,
                    'hp': 100,
                    'ammo': 10,
                    'ready': False
                }
                print(f"Player {player_id} UDP port: {udp_port}")
            
            # Gửi trạng thái chờ ban đầu
            client_socket.send("WAITING_FOR_PLAYERS".encode())
            
            while self.running:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                    
                if data == "READY":
                    self.players[player_id]['ready'] = True
                    self.ready_players.add(player_id)
                    print(f"Player {player_id} is ready")
                    self.check_game_start()
                    
                elif data == "RESTART":
                    self.handle_restart_request(player_id)
                    
        except Exception as e:
            print(f"Error with player {player_id}: {e}")
        finally:
            self.remove_player(player_id)
            client_socket.close()

    def handle_restart_request(self, player_id):
        """Xử lý yêu cầu restart từ client"""
        print(f"Player {player_id} requested restart")
        self.restart_requests.add(player_id)
        
        # Gửi xác nhận cho player
        try:
            self.players[player_id]['tcp_socket'].send("RESTART_ACCEPTED".encode())
        except:
            pass
        
        # Kiểm tra nếu cả 2 player đều request restart
        if len(self.restart_requests) >= 2:
            self.restart_game()

    def restart_game(self):
        """Khởi động lại game"""
        print("Restarting game...")
        
        # Reset tất cả trạng thái
        self.game_started = False
        self.ready_players.clear()
        self.restart_requests.clear()
        self.bullets.clear()
        self.game_state['game_over'] = False
        self.game_state['winner_id'] = None
        
        # Reset player positions và stats
        for pid, player in self.players.items():
            player['x'] = 100 if pid == '1' else 700
            player['y'] = 300
            player['angle'] = 0
            player['hp'] = 100
            player['ammo'] = 10
            player['ready'] = False
        
        # Gửi tín hiệu restart cho tất cả players
        for player in self.players.values():
            try:
                player['tcp_socket'].send("RESTART".encode())
            except:
                pass
        
        print("Game reset complete, waiting for players to ready up...")

    def check_game_start(self):
        """Kiểm tra và bắt đầu game nếu đủ player"""
        if len(self.ready_players) >= 2 and not self.game_started:
            self.start_game()

    def start_game(self):
        """Bắt đầu game mới"""
        self.game_started = True
        self.restart_requests.clear()
        print("Starting game with 2 players!")
        
        # Gửi tín hiệu bắt đầu game cho tất cả players
        for player in self.players.values():
            try:
                player['tcp_socket'].send("GAME_START".encode())
            except:
                pass

    def remove_player(self, player_id):
        """Xóa player khỏi game"""
        if player_id in self.players:
            print(f"Player {player_id} disconnected")
            del self.players[player_id]
            self.ready_players.discard(player_id)
            self.restart_requests.discard(player_id)

    def handle_udp_data(self):
        """Xử lý dữ liệu UDP từ clients"""
        while self.running:
            try:
                data, address = self.udp_socket.recvfrom(1024)
                message = json.loads(data.decode())
                player_id = message.get('id')
                
                if player_id in self.players and self.game_started:
                    self.process_player_message(player_id, message)
                    
            except Exception as e:
                print(f"UDP error: {e}")

    def process_player_message(self, player_id, message):
        """Xử lý message từ player"""
        player = self.players[player_id]
        
        # Cập nhật vị trí
        if 'x' in message and 'y' in message and 'angle' in message:
            player['x'] = max(20, min(780, message['x']))
            player['y'] = max(20, min(580, message['y']))
            player['angle'] = message['angle']
        
        # Xử lý bắn đạn
        if message.get('fire') and player['ammo'] > 0 and not self.game_state['game_over']:
            player['ammo'] -= 1
            self.bullets.append({
                'x': player['x'],
                'y': player['y'],
                'angle': player['angle'],
                'speed': 10,
                'owner': player_id
            })
        
        # Xử lý reload
        if message.get('reload'):
            player['ammo'] = 10
        
        # Cập nhật ammo
        if 'ammo_update' in message:
            player['ammo'] = message['ammo_update']

    def update_game(self):
        """Cập nhật game state"""
        while self.running:
            if self.game_started and not self.game_state['game_over']:
                # Di chuyển đạn
                for bullet in self.bullets[:]:
                    bullet['x'] += bullet['speed'] * math.cos(math.radians(bullet['angle']))
                    bullet['y'] += bullet['speed'] * math.sin(math.radians(bullet['angle']))
                    
                    # Kiểm tra va chạm với tường
                    if (bullet['x'] < 0 or bullet['x'] > 800 or 
                        bullet['y'] < 0 or bullet['y'] > 600):
                        self.bullets.remove(bullet)
                        continue
                    
                    # Kiểm tra va chạm với players
                    for pid, player in self.players.items():
                        if pid != bullet['owner']:
                            distance = math.sqrt((bullet['x'] - player['x'])**2 + 
                                               (bullet['y'] - player['y'])**2)
                            if distance < 25:  # Va chạm
                                player['hp'] -= 25
                                if bullet in self.bullets:
                                    self.bullets.remove(bullet)
                                
                                # Kiểm tra game over
                                if player['hp'] <= 0:
                                    self.end_game(winner_id=bullet['owner'])
                                break
                
                # Cập nhật game state
                self.update_game_state()
                
                # Gửi game state tới tất cả players
                self.broadcast_game_state()
            
            time.sleep(1/60)  # 60 FPS

    def update_game_state(self):
        """Cập nhật game state từ player data"""
        self.game_state['players'] = {}
        for pid, player in self.players.items():
            self.game_state['players'][pid] = {
                'x': player['x'],
                'y': player['y'], 
                'angle': player['angle'],
                'hp': player['hp'],
                'ammo': player['ammo']
            }
        self.game_state['bullets'] = self.bullets.copy()

    def end_game(self, winner_id):
        """Kết thúc game"""
        self.game_started = False
        self.game_state['game_over'] = True
        self.game_state['winner_id'] = winner_id
        print(f"Game over! Winner: {winner_id}")
        
        # Gửi game state cuối cùng
        self.broadcast_game_state()

    def broadcast_game_state(self):
        """Gửi game state tới tất cả players"""
        game_data = json.dumps(self.game_state).encode()
        for player in self.players.values():
            try:
                self.udp_socket.sendto(game_data, player['udp_address'])
            except:
                pass

    def start(self):
        """Khởi động server"""
        # Bắt đầu nhận kết nối TCP
        threading.Thread(target=self.accept_tcp_connections, daemon=True).start()
        
        # Bắt đầu xử lý UDP
        threading.Thread(target=self.handle_udp_data, daemon=True).start()
        
        # Bắt đầu game loop
        threading.Thread(target=self.update_game, daemon=True).start()
        
        print("Server is running...")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down server...")
            self.running = False

    def accept_tcp_connections(self):
        """Chấp nhận kết nối TCP mới"""
        while self.running:
            try:
                client_socket, address = self.tcp_socket.accept()
                if len(self.players) < 2:  # Giới hạn 2 players
                    threading.Thread(
                        target=self.handle_tcp_client,
                        args=(client_socket, address),
                        daemon=True
                    ).start()
                else:
                    client_socket.send("SERVER_FULL".encode())
                    client_socket.close()
            except Exception as e:
                print(f"TCP accept error: {e}")

if __name__ == "__main__":
    server = TankServer()
    server.start()