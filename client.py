# client.py
import socket
import json
import threading
import pygame
import math
import time

class TankGame:
    def __init__(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.host = 'localhost'
        self.host = input("Nhập địa chỉ IP của server (để trống cho localhost): ").strip()
        if not self.host:
            self.host = 'localhost'
        self.tcp_port = 5555
        self.udp_port = 5556
        self.player_id = None
        self.game_state = None
        self.running = True
        
        # Game state flags
        self.ready = False
        self.game_started = False
        self.waiting_for_players = True
        
        # Game mechanics
        self.last_fire_time = 0
        self.fire_cooldown = 0.5
        self.ammo_count = 10
        self.max_ammo = 10
        self.reloading = False
        self.reload_start_time = 0
        self.reload_duration = 7.0
        self.game_over = False
        self.winner_id = None
        self.waiting_for_restart = False

    def handle_restart(self):
        """Reset client state when game restarts"""
        self.ammo_count = 10
        self.reloading = False
        self.game_over = False
        self.winner_id = None
        self.waiting_for_restart = False
        self.last_fire_time = 0
        self.ready = False  # Reset ready status
        # KHÔNG đặt game_started = True ở đây, phải chờ server

    def connect(self):
        """Kết nối tới server và thiết lập communication"""
        try:
            # Connect TCP socket
            self.tcp_socket.connect((self.host, self.tcp_port))
            
            # Nhận player ID từ server
            self.player_id = self.tcp_socket.recv(1024).decode()
            print(f"Connected as Player {self.player_id}")
            
            # Bind UDP socket và gửi port cho server
            self.udp_socket.bind(('', 0))
            local_udp_port = self.udp_socket.getsockname()[1]
            self.tcp_socket.send(f"UDP_PORT:{local_udp_port}".encode())

            # Bắt đầu các thread nhận dữ liệu
            threading.Thread(target=self.receive_udp_data, daemon=True).start()
            threading.Thread(target=self.receive_tcp_data, daemon=True).start()
            
        except Exception as e:
            print(f"Connection error: {e}")
            self.running = False

    def receive_tcp_data(self):
        while self.running:
            try:
                data = self.tcp_socket.recv(1024).decode()
                if not data:
                    break
                        
                print(f"Received TCP: {data}")
                        
                if data == "RESTART":
                    self.handle_restart()
                    print("Game restarted!")
                elif data == "GAME_START":
                    self.game_started = True
                    self.waiting_for_players = False
                    self.game_over = False  # Đảm bảo reset game over
                    print("Game started!")
                elif data == "WAITING_FOR_PLAYERS":
                    self.waiting_for_players = True
                    self.game_started = False
                    print("Waiting for more players...")
                elif data == "SERVER_FULL":
                    print("Server is full! Cannot join.")
                    self.running = False
                elif data == "RESTART_ACCEPTED":
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
                (self.host, self.udp_port)
            )
        except Exception as e:
            print(f"UDP send error: {e}")

    def send_ready_status(self):
        """Gửi trạng thái ready tới server"""
        try:
            self.tcp_socket.send("READY".encode())
            self.ready = True
            print("Ready status sent to server")
        except Exception as e:
            print(f"Error sending ready status: {e}")

    def send_restart_request(self):
        """Gửi yêu cầu restart game"""
        try:
            self.tcp_socket.send("RESTART".encode())
            self.waiting_for_restart = True
            print("Restart request sent to server")
        except Exception as e:
            print(f"Error sending restart request: {e}")

    def start_reload(self):
        """Bắt đầu quá trình reload"""
        if not self.reloading and self.ammo_count < self.max_ammo and self.game_started and not self.game_over:
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
            
            if elapsed >= self.reload_duration:
                # Reload complete
                self.ammo_count = self.max_ammo
                self.reloading = False
                # Gửi ammo update tới server
                self.send_udp_data({
                    'id': self.player_id,
                    'ammo_update': self.ammo_count
                })
                return True
        return False

    def draw_waiting_screen(self, screen, big_font, font):
        """Vẽ màn hình chờ khi chưa bắt đầu game"""
        screen.fill((0, 0, 50))  # Dark blue background
        
        # Title
        title_text = big_font.render("TANK BATTLE", True, (255, 255, 0))
        title_rect = title_text.get_rect(center=(400, 150))
        screen.blit(title_text, title_rect)
        
        # Player ID
        id_text = font.render(f"Player ID: {self.player_id}", True, (0, 255, 255))
        id_rect = id_text.get_rect(center=(400, 220))
        screen.blit(id_text, id_rect)
        
        # Status message
        if self.waiting_for_players:
            status_text = font.render("Waiting for more players to join...", True, (255, 255, 0))
        elif self.ready:
            status_text = font.render("READY - Waiting for other players...", True, (0, 255, 0))
        else:
            status_text = font.render("Press SPACE to ready up", True, (255, 200, 0))
        
        status_rect = status_text.get_rect(center=(400, 270))
        screen.blit(status_text, status_rect)
        
        # Player count info
        if self.game_state and 'players' in self.game_state:
            player_count = len(self.game_state['players'])
            count_text = font.render(f"Players connected: {player_count}/2", True, (200, 200, 255))
            count_rect = count_text.get_rect(center=(400, 320))
            screen.blit(count_text, count_rect)
        
        # Instructions
        instructions = [
            "CONTROLS:",
            "ARROW KEYS - Move tank and aim",
            "SPACE - Fire weapon",
            "R - Reload ammo",
            "T - Restart (after game over)"
        ]
        
        for i, line in enumerate(instructions):
            text = font.render(line, True, (200, 200, 200))
            screen.blit(text, (250, 370 + i * 40))

    def draw_game_state(self, screen):
        """Vẽ game state (players, bullets, etc.)"""
        # Draw players
        for pid, player in self.game_state['players'].items():
            color = (0, 255, 0) if pid == self.player_id else (255, 0, 0)
            pygame.draw.circle(screen, color, (int(player['x']), int(player['y'])), 20)
            
            # Draw tank turret
            end_x = player['x'] + 25 * math.cos(math.radians(player['angle']))
            end_y = player['y'] + 25 * math.sin(math.radians(player['angle']))
            pygame.draw.line(screen, color, (player['x'], player['y']), (end_x, end_y), 5)
            
            # Draw HP bar
            pygame.draw.rect(screen, (255,0,0), (player['x']-25, player['y']-40, 50, 5))
            pygame.draw.rect(screen, (0,255,0), (player['x']-25, player['y']-40, player['hp']/2, 5))

        # Draw bullets
        for bullet in self.game_state['bullets']:
            pygame.draw.circle(screen, (255, 255, 0), (int(bullet['x']), int(bullet['y'])), 5)
            
            # Draw bullet trail
            trail_length = 10
            start_x = bullet['x'] - trail_length * math.cos(math.radians(bullet['angle']))
            start_y = bullet['y'] - trail_length * math.sin(math.radians(bullet['angle']))
            pygame.draw.line(screen, (255, 200, 0), 
                            (start_x, start_y), 
                            (bullet['x'], bullet['y']), 2)

    def draw_hud(self, screen, font):
        """Vẽ HUD với thông tin game"""
        # Draw ammo counter
        ammo_color = (255, 255, 255)
        if self.ammo_count == 0:
            ammo_color = (255, 0, 0)
        elif self.ammo_count <= 3:
            ammo_color = (255, 165, 0)
            
        ammo_text = font.render(f"Ammo: {self.ammo_count}/{self.max_ammo}", True, ammo_color)
        screen.blit(ammo_text, (10, 10))
        
        # Draw fire cooldown indicator
        fire_cooldown_percent = min(1.0, (time.time() - self.last_fire_time) / self.fire_cooldown)
        pygame.draw.rect(screen, (100, 100, 100), (10, 50, 200, 20))
        pygame.draw.rect(screen, (0, 200, 0), (10, 50, 200 * fire_cooldown_percent, 20))
        fire_text = font.render("Fire Cooldown", True, (255, 255, 255))
        screen.blit(fire_text, (10, 30))
        
        # Draw reload indicator
        if self.reloading:
            reload_progress = min(1.0, (time.time() - self.reload_start_time) / self.reload_duration)
            pygame.draw.rect(screen, (100, 100, 100), (10, 100, 200, 20))
            pygame.draw.rect(screen, (0, 100, 255), (10, 100, 200 * reload_progress, 20))
            
            # Show reload time remaining
            time_left = self.reload_duration - (time.time() - self.reload_start_time)
            reload_text = font.render(f"Reloading: {time_left:.1f}s", True, (255, 255, 255))
            screen.blit(reload_text, (220, 100))
        else:
            # Draw reload instruction if out of ammo or low ammo
            if self.ammo_count == 0 and not self.game_over:
                reload_text = font.render("Press R to reload (7s)", True, (255, 255, 0))
                screen.blit(reload_text, (10, 80))
            elif self.ammo_count <= 3 and not self.game_over:
                reload_text = font.render("Low ammo! Press R to reload", True, (255, 165, 0))
                screen.blit(reload_text, (10, 80))

    def draw_game_over(self, screen, big_font, font):
        """Vẽ màn hình game over"""
        # Semi-transparent overlay
        overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Determine winner text
        if self.winner_id == self.player_id:
            winner_text = big_font.render("VICTORY!", True, (0, 255, 0))
        elif self.winner_id is None:
            winner_text = big_font.render("DRAW GAME!", True, (255, 255, 0))
        else:
            winner_text = big_font.render("DEFEAT!", True, (255, 0, 0))
        
        text_rect = winner_text.get_rect(center=(400, 250))
        screen.blit(winner_text, text_rect)
        
        # Show restart instruction
        if self.waiting_for_restart:
            restart_text = font.render("Waiting for other players...", True, (255, 255, 255))
        else:
            restart_text = font.render("Press T to play again", True, (255, 255, 255))
        
        restart_rect = restart_text.get_rect(center=(400, 350))
        screen.blit(restart_text, restart_rect)

    def get_current_position(self):
        """Lấy vị trí hiện tại của player"""
        if self.game_state and self.player_id in self.game_state['players']:
            p = self.game_state['players'][self.player_id]
            return p['x'], p['y'], p['angle']
        return 400, 300, 0

    def run(self):
        """Main game loop"""
        pygame.init()
        screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Tank Battle - Player " + str(self.player_id))
        clock = pygame.time.Clock()
        font = pygame.font.SysFont(None, 36)
        big_font = pygame.font.SysFont(None, 72)

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
                self.draw_waiting_screen(screen, big_font, font)
                pygame.display.flip()
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
                    current_time - self.last_fire_time > self.fire_cooldown and 
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

            # Draw game state
            screen.fill((0, 0, 0))
            if self.game_state:
                self.draw_game_state(screen)
            
            # Draw HUD
            self.draw_hud(screen, font)
            
            # Draw game over screen if game is over
            if self.game_over:
                self.draw_game_over(screen, big_font, font)
            
            pygame.display.flip()
            clock.tick(30)

        # Cleanup
        pygame.quit()
        self.tcp_socket.close()
        self.udp_socket.close()

if __name__ == "__main__":
    game = TankGame()
    game.connect()
    game.run()