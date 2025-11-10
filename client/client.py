import socket
import threading
import json
import pygame
import math
import time
import argparse
import sys

from client.gui import GameRenderer
from common.messages import MessageTypes, GameConstants

class TankGame:
    def __init__(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Phân tích tham số CLI tuỳ chọn cho chế độ tự động
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('--auto', action='store_true', help='Auto-login mode (skip interactive prompts)')
        parser.add_argument('--host')
        parser.add_argument('--auth-type', choices=['login', 'register'])
        parser.add_argument('--username')
        parser.add_argument('--password')
        parser.add_argument('--name')
        try:
            self.cli_args = parser.parse_args(sys.argv[2:])
        except Exception:
            self.cli_args = argparse.Namespace(auto=False, host=None, auth_type=None, username=None, password=None, name=None)

    # Xác định host: tham số CLI > nhập tương tác > localhost
        if getattr(self.cli_args, 'host', None):
            self.host = self.cli_args.host or 'localhost'
        else:
            self.host = input("Nhập địa chỉ IP của server (để trống cho localhost): ").strip()
            if self.host == '0' or self.host == '':
                self.host = 'localhost'
        self.player_id = None
        self.game_state = None
        self.running = True
        
    # Cờ trạng thái trò chơi
        self.ready = False
        self.game_started = False
        self.waiting_for_players = True
        
    # Cơ chế trò chơi
        self.last_fire_time = 0
        self.ammo_count = GameConstants.MAX_AMMO
        self.reloading = False
        self.reload_start_time = 0
        self.game_over = False
        self.winner_id = None
        self.waiting_for_restart = False
        
    # Vị trí và góc hướng của người chơi (lưu cục bộ)
        self.player_x = 400
        self.player_y = 300
        self.player_angle = 0
        
    # Giao diện
        self.renderer = None
        self.gui_auth = None

        self.authenticated = False
        self.player_db_id = None
        self.username = None

    def authenticate(self):
        """Xác thực người dùng"""
        print("\n=== Fire Tank Online ===")

        # Nếu có dữ liệu auth từ GUI, dùng nó
        if getattr(self, 'gui_auth', None):
            gui = self.gui_auth
            username = gui.get('username')
            password = gui.get('password')
            auth_type = gui.get('type', 'login')
            # Có thể override host nếu GUI cung cấp
            if gui.get('host'):
                self.host = gui.get('host')
            auth_data = {'type': auth_type, 'username': username, 'password': password}
            if auth_type == 'register' and gui.get('name'):
                auth_data['name'] = gui.get('name')
        else:
            # Nếu chế độ auto qua CLI có credentials, dùng chúng
            if getattr(self, 'cli_args', None) and getattr(self.cli_args, 'auto', False) and self.cli_args.username and self.cli_args.password:
                username = self.cli_args.username
                password = self.cli_args.password
                auth_type = self.cli_args.auth_type or 'login'
                auth_data = {
                    'type': auth_type,
                    'username': username,
                    'password': password
                }
                if auth_type == 'register' and getattr(self.cli_args, 'name', None):
                    auth_data['name'] = self.cli_args.name
                print(f"Auto auth: username={username}, type={auth_type}")
            else:
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
            # Gửi dữ liệu xác thực
            json_data = json.dumps(auth_data)
            print(f"🔄 Đang gửi auth data: {json_data}")
            self.tcp_socket.send(json_data.encode())
            
            # Nhận phản hồi từ server
            response_data = self.tcp_socket.recv(1024).decode()
            print(f"📨 Nhận response: {response_data}")  # Gỡ lỗi
            
            if not response_data:
                print("❌ Không nhận được phản hồi từ server")
                return False
                
            response = json.loads(response_data)
            
            if response.get('success'):
                self.authenticated = True
                self.player_db_id = response.get('player_id')
                self.player_id = str(self.player_db_id)  # Gán player_id ngay tại đây
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
            # Khởi tạo renderer sớm để sử dụng màn hình đăng nhập GUI nếu cần
            self.renderer = GameRenderer(self.username or '')
            try:
                self.renderer.initialize()
            except Exception:
                # Nếu pygame không khả dụng trong môi trường hiện tại, ta vẫn tiếp tục (fallback CLI)
                pass

            # Nếu không ở chế độ auto CLI, hiển thị màn hình login GUI để nhập host/credentials
            if not (getattr(self, 'cli_args', None) and getattr(self.cli_args, 'auto', False)):
                gui_auth = None
                try:
                    gui_auth = self.renderer.show_login_screen()
                except Exception:
                    gui_auth = None

                if gui_auth is None:
                    print("Login canceled or GUI closed.")
                    self.running = False
                    return
                # Lưu thông tin từ GUI
                self.gui_auth = gui_auth
                if gui_auth.get('host'):
                    self.host = gui_auth.get('host')

            # Kết nối TCP
            self.tcp_socket.connect((self.host, GameConstants.TCP_PORT))

            # Thực hiện xác thực
            if not self.authenticate():
                self.running = False
                return

            # Cập nhật renderer với player id đã nhận
            self.renderer.set_player_id(self.player_id)
            
            # Thiết lập UDP
            self.udp_socket.bind(('', 0))
            local_udp_port = self.udp_socket.getsockname()[1]
            self.tcp_socket.send(f"UDP_PORT:{local_udp_port}".encode())
            
            print(f"Connected as Player {self.player_id} ({self.username})")
            
            # Bắt đầu các thread để nhận dữ liệu
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
    # Đặt lại vị trí người chơi
        self.player_x = 400
        self.player_y = 300
        self.player_angle = 0

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
                
                # Cập nhật số đạn và vị trí từ server
                if self.game_state and 'players' in self.game_state:
                    player_data = self.game_state['players'].get(self.player_id)
                    if player_data:
                        if 'ammo' in player_data:
                            self.ammo_count = player_data['ammo']
                        # Cập nhật vị trí từ server để đồng bộ hoá
                        self.player_x = player_data.get('x', self.player_x)
                        self.player_y = player_data.get('y', self.player_y)
                        self.player_angle = player_data.get('angle', self.player_angle)
                
                # Kiểm tra điều kiện kết thúc trận
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

    def send_player_update(self):
        """Gửi cập nhật vị trí và trạng thái player tới server"""
        update_data = {
            'id': str(self.player_id),
            'x': self.player_x,
            'y': self.player_y,
            'angle': self.player_angle
        }
        self.send_udp_data(update_data)

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
    # Chỉ cho phép nạp đạn khi trận đấu đang chạy và chưa ở trạng thái nạp.
    # Giữ kiểm tra rằng số đạn phải nhỏ hơn tối đa để tránh nạp thừa.
        if not self.reloading and self.game_started and not self.game_over and self.ammo_count < GameConstants.MAX_AMMO:
            self.reloading = True
            self.reload_start_time = time.time()
            # Gửi lệnh nạp đạn qua UDP (real-time) và qua TCP như fallback đáng tin cậy
            reload_msg = {
                'id': self.player_id,
                'reload': True
            }
            self.send_udp_data(reload_msg)
            try:
                # Gửi một marker TCP ngắn để server nhận được ý định nạp đạn một cách đáng tin cậy
                # Server sẽ chấp nhận chuỗi thuần 'RELOAD' như fallback
                if self.tcp_socket:
                    self.tcp_socket.send(b'RELOAD')
            except Exception as e:
                print(f"Error sending reload via TCP fallback: {e}")

    def update_reload(self):
        """Cập nhật trạng thái reload"""
        if self.reloading:
            current_time = time.time()
            elapsed = current_time - self.reload_start_time
            
            if elapsed >= GameConstants.RELOAD_DURATION:
                # Hoàn tất nạp đạn
                self.ammo_count = GameConstants.MAX_AMMO
                self.reloading = False
                # Gửi cập nhật số đạn tới server
                self.send_udp_data({
                    'id': self.player_id,
                    'ammo_update': self.ammo_count
                })
                return True
        return False

    def handle_movement(self):
        """Xử lý di chuyển của player"""
        keys = pygame.key.get_pressed()
        
    # Xử lý di chuyển
        if keys[pygame.K_LEFT]:
            self.player_angle -= 5
        if keys[pygame.K_RIGHT]:
            self.player_angle += 5
        if keys[pygame.K_UP]:
            self.player_x += 5 * math.cos(math.radians(self.player_angle))
            self.player_y += 5 * math.sin(math.radians(self.player_angle))
        if keys[pygame.K_DOWN]:
            self.player_x -= 5 * math.cos(math.radians(self.player_angle))
            self.player_y -= 5 * math.sin(math.radians(self.player_angle))
        
    # Giới hạn vị trí trong khu vực màn hình
        self.player_x = max(20, min(GameConstants.SCREEN_WIDTH - 20, self.player_x))
        self.player_y = max(20, min(GameConstants.SCREEN_HEIGHT - 20, self.player_y))

    def handle_firing(self, current_time):
        """Xử lý bắn đạn"""
        keys = pygame.key.get_pressed()
        
        if (keys[pygame.K_SPACE] and 
            current_time - self.last_fire_time > GameConstants.FIRE_COOLDOWN and 
            self.ammo_count > 0 and 
            not self.reloading and
            self.game_started and not self.game_over):
            
            self.send_udp_data({
                'id': self.player_id,
                'fire': True,
                'x': self.player_x,
                'y': self.player_y,
                'angle': self.player_angle
            })
            self.last_fire_time = current_time
            self.ammo_count -= 1

    def run(self):
        """Main game loop"""
        if not self.renderer:
            return
            
        clock = pygame.time.Clock()

        while self.running:
            current_time = time.time()
            
            # Cập nhật trạng thái nạp đạn
            self.update_reload()
            
            # Xử lý sự kiện Pygame
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

            # Nếu trận chưa bắt đầu, hiển thị màn chờ
            if not self.game_started:
                self.renderer.draw_waiting_screen(self.game_state, self.ready, self.waiting_for_players)
                self.renderer.update_display()
                clock.tick(30)
                continue

            # Xử lý input khi game đang chạy và chưa kết thúc
            if self.game_started and not self.game_over:
                # Xử lý di chuyển
                self.handle_movement()
                
                # Xử lý hành vi bắn đạn
                self.handle_firing(current_time)
                
                # Gửi cập nhật vị trí tới server
                self.send_player_update()

            # Vẽ trò chơi
            self.renderer.screen.fill((0, 0, 0))
            if self.game_state:
                self.renderer.draw_game_state(self.game_state)
            
            # Vẽ HUD
            self.renderer.draw_hud(
                self.ammo_count, 
                GameConstants.MAX_AMMO,
                self.reloading,
                self.reload_start_time,
                self.last_fire_time,
                self.game_over
            )
            
            # Vẽ màn hình kết thúc nếu trận đấu đã kết thúc
            if self.game_over:
                self.renderer.draw_game_over(self.winner_id, self.waiting_for_restart)
            
            self.renderer.update_display()
            clock.tick(60)  # Tăng FPS lên 60 để mượt hơn

        # Cleanup
        self.renderer.cleanup()
        self.tcp_socket.close()
        self.udp_socket.close()

if __name__ == "__main__":
    game = TankGame()
    game.connect()
    game.run()