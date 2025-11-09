import socket
import threading
import json
import pygame
import math
import time

from client.gui import GameRenderer
from common.messages import MessageTypes, GameConstants

class TankGame:
    def __init__(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host = input("Nhập địa chỉ IP của server (để trống cho localhost): ").strip()
        if self.host == '0' or self.host == '':
            self.host = 'localhost'
        self.player_id = None
        self.game_state = None
        self.running = True
        
        # Game state flags
        self.ready = False
        self.game_started = False
        self.waiting_for_players = True
        
        # Game mechanics
        self.last_fire_time = 0
        self.ammo_count = GameConstants.MAX_AMMO
        self.reloading = False
        self.reload_start_time = 0
        self.game_over = False
        self.winner_id = None
        self.waiting_for_restart = False
        
        # GUI
        self.renderer = None
        
        self.authenticated = False
        self.player_db_id = None
        self.username = None

    def authenticate(self):
        """Xác thực người dùng"""
        print("\n=== Fire Tank Online ===")
        print("1. Đăng nhập")
        print("2. Đăng ký")
        
        choice = input("Chọn option (1/2): ").strip()
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        
        auth_type = 'login' if choice == '1' else 'register'
        auth_data = {
            'type': auth_type,
            'username': username,
            'password': password
        }
        
        if auth_type == 'register':
            name = input("Tên hiển thị (để trống dùng username): ").strip()
            if name:
                auth_data['name'] = name
        
        try:
            # Gửi thông tin xác thực
            json_data = json.dumps(auth_data)
            print(f"🔄 Đang gửi auth data: {json_data}")
            self.tcp_socket.send(json_data.encode())
            
            # Nhận phản hồi
            response_data = self.tcp_socket.recv(1024).decode()
            print(f"📨 Nhận response: {response_data}")  # Debug
            
            if not response_data:
                print("❌ Không nhận được phản hồi từ server")
                return False
                
            response = json.loads(response_data)
            
            if response.get('success'):
                self.authenticated = True
                self.player_db_id = response.get('player_id')
                self.username = username
                print(f"✅ Đăng nhập thành công! ID: {self.player_db_id}")
                return True
            else:
                print(f"❌ Lỗi: {response.get('message')}")
                return False
                
        except json.JSONDecodeError as e:
            print(f"❌ Lỗi parse JSON từ server: {e}")
            print(f"📨 Dữ liệu nhận được: {response_data}")
            return False
        except Exception as e:
            print(f"❌ Lỗi xác thực: {e}")
            import traceback
            traceback.print_exc()
            return False
    def connect(self):
        """Kết nối tới server với xác thực"""
        try:
            # Connect TCP socket
            self.tcp_socket.connect((self.host, GameConstants.TCP_PORT))
            
            # Xác thực
            if not self.authenticate():
                self.running = False
                return
                
            # Khởi tạo renderer trước
            self.renderer = GameRenderer(self.username)
            self.renderer.initialize()
            
            # Thiết lập UDP
            self.udp_socket.bind(('', 0))
            local_udp_port = self.udp_socket.getsockname()[1]
            self.tcp_socket.send(f"UDP_PORT:{local_udp_port}".encode())
            
            # Nhận player ID từ server và cập nhật renderer
            self.player_id = self.tcp_socket.recv(1024).decode()
            self.renderer.set_player_id(self.player_id)  # Cập nhật player_id trong renderer
            print(f"Connected as Player {self.player_id} ({self.username})")
            
            # Bắt đầu các thread nhận dữ liệu
            threading.Thread(target=self.receive_udp_data, daemon=True).start()
            threading.Thread(target=self.receive_tcp_data, daemon=True).start()
            
        except Exception as e:
            print(f"Connection error: {e}")
            self.running = False

    def handle_restart(self):
        """Reset client state khi game restart"""
        self.ammo_count = GameConstants.MAX_AMMO
        self.reloading = False
        self.game_over = False
        self.winner_id = None
        self.waiting_for_restart = False
        self.last_fire_time = 0
        self.ready = False
        
    def handle_server_message(self, data):
        message_type = data.get('type')
        
        if message_type == 'map_info':
            # Nhận thông tin map từ server
            map_id = data.get('map_id', 0)
            print(f"Received map info from server: map_id={map_id}")
            self.game_renderer.set_map(map_id)
        
        elif message_type == 'game_state':
            # Xử lý game state
            game_state = data.get('state', {})
            # Kiểm tra nếu game state có chứa map_id
            if 'map_id' in game_state:
                map_id = game_state['map_id']
                if not self.game_renderer.map_initialized or self.game_renderer.get_current_map_id() != map_id:
                    print(f"Setting map from game_state: {map_id}")
                    self.game_renderer.set_map(map_id)
            
            # Cập nhật game state
            self.game_state = game_state

    def receive_tcp_data(self):
        """Nhận dữ liệu TCP từ server"""
        while self.running:
            try:
                data = self.tcp_socket.recv(1024).decode()
                if not data:
                    break
                        
                print(f"Received TCP: {data}")
                        
                if data == MessageTypes.RESTART:
                    self.handle_restart()
                    print("Game restarted!")
                elif data == MessageTypes.GAME_START:
                    self.game_started = True
                    self.waiting_for_players = False
                    self.game_over = False
                    print("Game started!")
                elif data == MessageTypes.WAITING_FOR_PLAYERS:
                    self.waiting_for_players = True
                    self.game_started = False
                    print("Waiting for more players...")
                elif data == MessageTypes.SERVER_FULL:
                    print("Server is full! Cannot join.")
                    self.running = False
                elif data == MessageTypes.RESTART_ACCEPTED:
                    self.waiting_for_restart = True
                    print("Restart request accepted, waiting for other player...")
                            
            except Exception as e:
                print(f"TCP receive error: {e}")
                break

    def receive_udp_data(self):
        """Nhận game state từ server qua UDP"""
        while self.running:
            try:
                data, _ = self.udp_socket.recvfrom(1024)
                game_state = json.loads(data.decode())
                self.game_state = game_state
                
                # Update ammo count từ server
                if self.game_state and 'players' in self.game_state:
                    player_data = self.game_state['players'].get(self.player_id)
                    if player_data and 'ammo' in player_data:
                        self.ammo_count = player_data['ammo']
                
                # Kiểm tra game over condition
                if 'game_over' in self.game_state and self.game_state['game_over']:
                    self.game_over = True
                    self.winner_id = self.game_state.get('winner_id')
                    self.game_started = False
                else:
                    self.game_over = False
                    self.winner_id = None
                    
            except Exception as e:
                print(f"UDP receive error: {e}")
                break

    def send_udp_data(self, data):
        """Gửi dữ liệu gameplay tới server qua UDP"""
        try:
            self.udp_socket.sendto(
                json.dumps(data).encode(),
                (self.host, GameConstants.UDP_PORT)
            )
        except Exception as e:
            print(f"UDP send error: {e}")

    def send_ready_status(self):
        """Gửi trạng thái ready tới server"""
        try:
            self.tcp_socket.send(MessageTypes.READY.encode())
            self.ready = True
            print("Ready status sent to server")
        except Exception as e:
            print(f"Error sending ready status: {e}")

    def send_restart_request(self):
        """Gửi yêu cầu restart game"""
        try:
            self.tcp_socket.send(MessageTypes.RESTART.encode())
            self.waiting_for_restart = True
            print("Restart request sent to server")
        except Exception as e:
            print(f"Error sending restart request: {e}")

    def start_reload(self):
        """Bắt đầu quá trình reload"""
        if not self.reloading and self.ammo_count < GameConstants.MAX_AMMO and self.game_started and not self.game_over:
            self.reloading = True
            self.reload_start_time = time.time()
            # Gửi reload command tới server
            self.send_udp_data({
                'id': self.player_id,
                'reload': True
            })

    def update_reload(self):
        """Cập nhật trạng thái reload"""
        if self.reloading:
            current_time = time.time()
            elapsed = current_time - self.reload_start_time
            
            if elapsed >= GameConstants.RELOAD_DURATION:
                # Reload complete
                self.ammo_count = GameConstants.MAX_AMMO
                self.reloading = False
                # Gửi ammo update tới server
                self.send_udp_data({
                    'id': self.player_id,
                    'ammo_update': self.ammo_count
                })
                return True
        return False

    def get_current_position(self):
        """Lấy vị trí hiện tại của player"""
        if self.game_state and self.player_id in self.game_state['players']:
            p = self.game_state['players'][self.player_id]
            return p['x'], p['y'], p['angle']
        return 400, 300, 0

    def run(self):
        """Main game loop"""
        if not self.renderer:
            return
            
        clock = pygame.time.Clock()

        while self.running:
            current_time = time.time()
            
            # Update reload status
            self.update_reload()
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if not self.game_started and not self.ready and event.key == pygame.K_SPACE:
                        self.send_ready_status()
                    elif event.key == pygame.K_r and self.game_started and not self.game_over:
                        self.start_reload()
                    elif event.key == pygame.K_t and self.game_over:
                        self.send_restart_request()
                        self.waiting_for_restart = True

            # If game hasn't started, show waiting screen
            if not self.game_started:
                self.renderer.draw_waiting_screen(self.game_state, self.ready, self.waiting_for_players)
                self.renderer.update_display()
                clock.tick(30)
                continue

            # Normal game input (when game is running and not over)
            if self.game_started and not self.game_over:
                keys = pygame.key.get_pressed()
                x, y, angle = self.get_current_position()
                
                # Handle movement
                if keys[pygame.K_LEFT]:
                    angle -= 5
                if keys[pygame.K_RIGHT]:
                    angle += 5
                if keys[pygame.K_UP]:
                    x += 5 * math.cos(math.radians(angle))
                    y += 5 * math.sin(math.radians(angle))
                if keys[pygame.K_DOWN]:
                    x -= 5 * math.cos(math.radians(angle))
                    y -= 5 * math.sin(math.radians(angle))
                
                # Handle firing
                if (keys[pygame.K_SPACE] and 
                    current_time - self.last_fire_time > GameConstants.FIRE_COOLDOWN and 
                    self.ammo_count > 0 and 
                    not self.reloading and
                    self.game_started):
                    
                    self.send_udp_data({
                        'id': self.player_id,
                        'fire': True,
                        'x': x,
                        'y': y,
                        'angle': angle
                    })
                    self.last_fire_time = current_time
                    self.ammo_count -= 1

                # Send position update
                self.send_udp_data({
                    'id': self.player_id,
                    'x': x,
                    'y': y,
                    'angle': angle
                })

            # Draw game
            self.renderer.screen.fill((0, 0, 0))
            if self.game_state:
                self.renderer.draw_game_state(self.game_state)
            
            # Draw HUD
            self.renderer.draw_hud(
                self.ammo_count, 
                GameConstants.MAX_AMMO,
                self.reloading,
                self.reload_start_time,
                self.last_fire_time,
                self.game_over
            )
            
            # Draw game over screen if game is over
            if self.game_over:
                self.renderer.draw_game_over(self.winner_id, self.waiting_for_restart)
            
            self.renderer.update_display()
            clock.tick(30)

        # Cleanup
        self.renderer.cleanup()
        self.tcp_socket.close()
        self.udp_socket.close()

if __name__ == "__main__":
    game = TankGame()
    game.connect()
    game.run()