import socket
import threading
import json
import time
from server.game import GameEngine
from common.messages import MessageTypes, GameConstants

class TankServer:
    def __init__(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host = '0.0.0.0'
        self.tcp_port = GameConstants.TCP_PORT
        self.udp_port = GameConstants.UDP_PORT
        self.game_engine = GameEngine()
        self.running = True
        
        # Bind sockets
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.udp_socket.bind((self.host, self.udp_port))
        self.tcp_socket.listen(GameConstants.MAX_PLAYERS)
        
        print(f"Server started on {self.host}:{self.tcp_port} (TCP) and {self.host}:{self.udp_port} (UDP)")

    def handle_tcp_client(self, client_socket, address):
        """Xử lý kết nối TCP từ client"""
        player_id = str(len(self.game_engine.players) + 1)
        print(f"Player {player_id} connected from {address}")
        
        # Gửi ID cho client
        client_socket.send(player_id.encode())
        
        try:
            # Nhận UDP port từ client
            data = client_socket.recv(1024).decode()
            if data.startswith("UDP_PORT:"):
                udp_port = int(data.split(":")[1])
                self.game_engine.add_player(player_id, (address[0], udp_port), client_socket)
                print(f"Player {player_id} UDP port: {udp_port}")
            
            # Gửi trạng thái chờ ban đầu
            client_socket.send(MessageTypes.WAITING_FOR_PLAYERS.encode())
            
            while self.running:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                    
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
                        
        except Exception as e:
            print(f"Error with player {player_id}: {e}")
        finally:
            self.game_engine.remove_player(player_id)
            client_socket.close()

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

    def start_game(self):
        """Bắt đầu game mới"""
        self.game_engine.start_game()
        print("Starting game with 2 players!")
        
        # Gửi tín hiệu bắt đầu game cho tất cả players
        for socket in self.game_engine.get_all_tcp_sockets():
            try:
                socket.send(MessageTypes.GAME_START.encode())
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