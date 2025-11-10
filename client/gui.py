import pygame
import math
import time
import random
import os
from common.messages import GameConstants


class GameRenderer:
    def __init__(self, username):
        self.player_name = username
        self.player_id = None  # Sẽ được gán sau
        self.screen = None
        self.font = None
        self.big_font = None
        self.original_width = GameConstants.SCREEN_WIDTH
        self.original_height = GameConstants.SCREEN_HEIGHT
        self.fullscreen = False
        self.current_size = (self.original_width, self.original_height)
        self.backgrounds = []
        self.current_background = None
        self.scaled_background = None
        self.current_map_id = 0  # ID của bản đồ hiện tại
        self.map_initialized = False

    def set_player_id(self, player_id):
        """Gán player ID sau khi nhận từ server"""
        self.player_id = player_id
        pygame.display.set_caption(f"Tank Battle - {self.player_name} (Player {self.player_id})")
        self.scaled_background = None

    def initialize(self):
        """Khởi tạo pygame và font"""
        pygame.init()
        self.screen = pygame.display.set_mode((self.original_width, self.original_height), pygame.RESIZABLE)
        pygame.display.set_caption(f"Tank Battle - Player {self.player_id}")
        self.font = pygame.font.SysFont(None, 36)
        self.big_font = pygame.font.SysFont(None, 72)

        # Tải các ảnh nền (background)
        self.load_backgrounds()
        # Đặt map mặc định ban đầu
        self.set_map(0)  # Map 0 làm mặc định

    def _draw_input_box(self, rect, text, active=False, password=False):
        """Vẽ hộp nhập liệu đơn giản và trả về rect để xử lý sự kiện"""
        color = (255, 255, 255) if active else (180, 180, 180)
        pygame.draw.rect(self.screen, (20, 20, 20), rect)
        pygame.draw.rect(self.screen, color, rect, 2)
        display_text = text
        if password:
            display_text = '*' * len(text)
        txt_surf = self.font.render(display_text, True, (230, 230, 230))
        txt_rect = txt_surf.get_rect(midleft=(rect.x + 8, rect.centery))
        self.screen.blit(txt_surf, txt_rect)

    def show_login_screen(self):
        """Hiển thị màn hình đăng nhập / đăng ký bằng Pygame. Trả về dict với host, type, username, password, name"""
        # Các trường input
        host = ''
        username = ''
        password = ''
        name = ''
        auth_type = 'login'  # hoặc 'register'

        active = 0  # 0:host,1:username,2:password,3:name
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_TAB:
                        active = (active + 1) % 4
                    elif event.key == pygame.K_RETURN:
                        # Nếu đang đăng nhập, ignore name field
                        if auth_type == 'login' or (auth_type == 'register' and username and password):
                            running = False
                    elif event.key == pygame.K_BACKSPACE:
                        if active == 0 and host:
                            host = host[:-1]
                        elif active == 1 and username:
                            username = username[:-1]
                        elif active == 2 and password:
                            password = password[:-1]
                        elif active == 3 and name:
                            name = name[:-1]
                    elif event.key == pygame.K_F1:
                        auth_type = 'login'
                    elif event.key == pygame.K_F2:
                        auth_type = 'register'
                    else:
                        ch = event.unicode
                        if ch:
                            if active == 0:
                                host += ch
                            elif active == 1:
                                username += ch
                            elif active == 2:
                                password += ch
                            elif active == 3:
                                name += ch

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    # tính active theo vị trí (đơn giản)
                    # Host box
                    hw = 400; hh = 40
                    cx, cy = self._get_center()
                    start_x = cx - hw//2
                    y0 = cy - 120
                    boxes = [pygame.Rect(start_x, y0, hw, hh),
                             pygame.Rect(start_x, y0 + 60, hw, hh),
                             pygame.Rect(start_x, y0 + 120, hw, hh),
                             pygame.Rect(start_x, y0 + 180, hw, hh)]
                    for i, r in enumerate(boxes):
                        if r.collidepoint(mx, my):
                            active = i

            # Vẽ UI
            self.screen.fill((10, 10, 30))
            title = self.big_font.render("Fire Tank - Login", True, (255, 220, 0))
            tx, ty = self._get_center()
            self.screen.blit(title, title.get_rect(center=(tx, 80)))

            hw = 400; hh = 40
            start_x = tx - hw//2
            y0 = 160

            # Host
            host_rect = pygame.Rect(start_x, y0, hw, hh)
            self._draw_input_box(host_rect, host or 'localhost', active == 0, password=False)
            host_label = self.font.render("Server IP (Enter for localhost)", True, (200,200,200))
            self.screen.blit(host_label, (start_x, y0 - 28))

            # Username
            user_rect = pygame.Rect(start_x, y0 + 60, hw, hh)
            self._draw_input_box(user_rect, username, active == 1)
            user_label = self.font.render("Username", True, (200,200,200))
            self.screen.blit(user_label, (start_x, y0 + 60 - 28))

            # Password
            pass_rect = pygame.Rect(start_x, y0 + 120, hw, hh)
            self._draw_input_box(pass_rect, password, active == 2, password=True)
            pass_label = self.font.render("Password", True, (200,200,200))
            self.screen.blit(pass_label, (start_x, y0 + 120 - 28))

            # Display name (for register)
            name_rect = pygame.Rect(start_x, y0 + 180, hw, hh)
            self._draw_input_box(name_rect, name, active == 3)
            name_label = self.font.render("Display name (register)", True, (180,180,180))
            self.screen.blit(name_label, (start_x, y0 + 180 - 28))

            # Auth type instructions
            info = self.font.render("Press F1 to Login, F2 to Register. Press ENTER to submit.", True, (220,220,220))
            self.screen.blit(info, info.get_rect(center=(tx, y0 + 260)))

            type_text = self.font.render(f"Mode: {auth_type.upper()}", True, (255,255,0))
            self.screen.blit(type_text, (start_x, y0 + 260 + 30))

            pygame.display.flip()
            clock.tick(30)

        # Nếu host rỗng, dùng localhost
        if not host or host.strip() == '':
            host = 'localhost'

        return {
            'host': host.strip(),
            'type': auth_type,
            'username': username.strip(),
            'password': password,
            'name': name.strip() if name.strip() else None
        }
    
    def set_map(self, map_id):
        """Thiết lập map dựa trên ID từ server"""
        print(f"Setting map to ID: {map_id}")
        if 0 <= map_id < len(self.backgrounds):
            self.current_map_id = map_id
            self.current_background = self.backgrounds[map_id]
            self._rescale_background()
            self.map_initialized = True
            return True
        else:
            print(f"Invalid map_id: {map_id}, available: 0-{len(self.backgrounds)-1}")
            # Dự phòng: chuyển về map đầu tiên
            if self.backgrounds:
                self.current_map_id = 0
                self.current_background = self.backgrounds[0]
                self._rescale_background()
                self.map_initialized = True
            return False
    
    def get_current_map_id(self):
        """Lấy ID của map hiện tại"""
        return self.current_map_id
    
    def load_backgrounds(self):
        """Load tất cả background images từ thư mục ui/"""
        background_dir = "ui"
    # Tạo thư mục nếu chưa tồn tại
        if not os.path.exists(background_dir):
            os.makedirs(background_dir)
            print(f"Created directory: {background_dir}")
        
        background_files = ["map1.png", "map2.png", "map3.png"]
        
        for bg_file in background_files:
            bg_path = os.path.join(background_dir, bg_file)
            try:
                if os.path.exists(bg_path):
                    background = pygame.image.load(bg_path).convert()
                    self.backgrounds.append(background)
                    print(f"Loaded background: {bg_file}")
                else:
                    print(f"Background file not found: {bg_path}")
                    # Tạo background mặc định nếu không tìm thấy file
                    self.create_default_background(background_files.index(bg_file))
            except Exception as e:
                print(f"Error loading background {bg_file}: {e}")
                self.create_default_background(background_files.index(bg_file))
        
    # Đảm bảo có ít nhất 3 ảnh nền
        while len(self.backgrounds) < 3:
            self.create_default_background(len(self.backgrounds))
        
        print(f"Total backgrounds loaded: {len(self.backgrounds)}")
    
    def create_default_background(self, map_id):
        """Tạo background mặc định dựa trên map_id"""
    # Màu sắc khác nhau cho mỗi bản đồ
        colors = [
            (30, 30, 60),   # Bản đồ 1: Xanh đậm
            (40, 60, 30),   # Bản đồ 2: Xanh lá
            (60, 30, 40)    # Bản đồ 3: Tím
        ]
        
        color = colors[map_id] if map_id < len(colors) else (50, 50, 50)
        bg = pygame.Surface((self.original_width, self.original_height))
        bg.fill(color)
        
    # Vẽ họa tiết đặc trưng cho mỗi bản đồ
        for i in range(0, self.original_width, 40):
            for j in range(0, self.original_height, 40):
                if map_id == 0:  # Bản đồ 1: chấm tròn
                    pygame.draw.circle(bg, (color[0] + 20, color[1] + 20, color[2] + 20), 
                                     (i + 20, j + 20), 3)
                elif map_id == 1:  # Bản đồ 2: hình vuông
                    pygame.draw.rect(bg, (color[0] + 20, color[1] + 20, color[2] + 20), 
                                   (i + 15, j + 15, 10, 10))
                else:  # Bản đồ 3: hình thoi
                    points = [(i + 20, j + 10), (i + 30, j + 20), 
                             (i + 20, j + 30), (i + 10, j + 20)]
                    pygame.draw.polygon(bg, (color[0] + 20, color[1] + 20, color[2] + 20), points)
        
    # Thêm chữ để nhận biết bản đồ
        font = pygame.font.SysFont(None, 48)
        text = font.render(f"MAP {map_id + 1}", True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.original_width // 2, self.original_height // 2))
        bg.blit(text, text_rect)
        
        self.backgrounds.append(bg)
        print(f"Created default background for map {map_id + 1}")
    
    def _rescale_background(self):
        """Scale background theo kích thước hiện tại"""
        if self.current_background:
            self.scaled_background = pygame.transform.scale(self.current_background, self.current_size)
            print(f"Background rescaled to: {self.current_size}")
    
    def toggle_fullscreen(self):
        """Chuyển đổi giữa chế độ fullscreen và windowed"""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            # Lấy kích thước màn hình hiện tại
            screen_info = pygame.display.Info()
            self.current_size = (screen_info.current_w, screen_info.current_h)
            self.screen = pygame.display.set_mode(self.current_size, pygame.FULLSCREEN)
        else:
            self.current_size = (self.original_width, self.original_height)
            self.screen = pygame.display.set_mode(self.current_size, pygame.RESIZABLE)
        self._rescale_background()
    
    def handle_resize(self, size):
        """Xử lý sự kiện thay đổi kích thước cửa sổ"""
        if not self.fullscreen:
            self.current_size = size
            self.screen = pygame.display.set_mode(self.current_size, pygame.RESIZABLE)
            self._rescale_background()
    
    def _scale_position(self, x, y):
        """Tính toán vị trí tỷ lệ dựa trên kích thước hiện tại"""
        scale_x = self.current_size[0] / self.original_width
        scale_y = self.current_size[1] / self.original_height
        return x * scale_x, y * scale_y
    
    def _scale_value(self, value, is_width=True):
        """Tính toán giá trị tỷ lệ (width hoặc height)"""
        if is_width:
            return value * (self.current_size[0] / self.original_width)
        else:
            return value * (self.current_size[1] / self.original_height)
    
    def _get_center(self):
        """Lấy vị trí trung tâm của màn hình hiện tại"""
        return self.current_size[0] // 2, self.current_size[1] // 2

    def draw_background(self):
        """Vẽ background"""
        if self.scaled_background:
            self.screen.blit(self.scaled_background, (0, 0))
        else:
            # Dự phòng: màu nền mặc định
            self.screen.fill((0, 0, 30))
    
    def draw_waiting_screen(self, game_state, ready, waiting_for_players):
        """Vẽ màn hình chờ"""
        self.draw_background()
        
    # Tạo overlay bán trong suốt để chữ dễ đọc hơn
        overlay = pygame.Surface(self.current_size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))  # Đen với độ trong suốt 50%
        self.screen.blit(overlay, (0, 0))
        
        center_x, center_y = self._get_center()
        
    # Tiêu đề
        title_text = self.big_font.render("TANK BATTLE", True, (255, 255, 0))
        title_rect = title_text.get_rect(center=(center_x, self._scale_value(150, False)))
        self.screen.blit(title_text, title_rect)
        
    # Hiển thị Player ID
        id_text = self.font.render(f"Player ID: {self.player_id}", True, (0, 255, 255))
        id_rect = id_text.get_rect(center=(center_x, self._scale_value(220, False)))
        self.screen.blit(id_text, id_rect)
        
    # Thông tin bản đồ (nếu đã có)
        if self.current_background:
            map_text = self.font.render(f"Map: {self.current_map_id + 1}", True, (200, 200, 100))
            map_rect = map_text.get_rect(center=(center_x, self._scale_value(260, False)))
            self.screen.blit(map_text, map_rect)
        
    # Thông điệp trạng thái
        if waiting_for_players:
            status_text = self.font.render("Waiting for more players to join...", True, (255, 255, 0))
        elif ready:
            status_text = self.font.render("READY - Waiting for other players...", True, (0, 255, 0))
        else:
            status_text = self.font.render("Press SPACE to ready up", True, (255, 200, 0))
        
        status_rect = status_text.get_rect(center=(center_x, self._scale_value(300, False)))
        self.screen.blit(status_text, status_rect)
        
    # Thông tin số người chơi
        if game_state and 'players' in game_state:
            player_count = len(game_state['players'])
            count_text = self.font.render(f"Players connected: {player_count}/2", True, (200, 200, 255))
            count_rect = count_text.get_rect(center=(center_x, self._scale_value(340, False)))
            self.screen.blit(count_text, count_rect)
        
    # Hướng dẫn điều khiển
        instructions = [
            "CONTROLS:",
            "ARROW KEYS - Move tank and aim",
            "SPACE - Fire weapon",
            "R - Reload ammo",
            "T - Restart (after game over)",
            "F - Toggle Fullscreen"
        ]
        
        for i, line in enumerate(instructions):
            text = self.font.render(line, True, (200, 200, 200))
            text_x = center_x - self._scale_value(150)
            text_y = self._scale_value(390, False) + i * self._scale_value(40, False)
            self.screen.blit(text, (text_x, text_y))

    def draw_game_state(self, game_state):
        """Vẽ game state (players, bullets, etc.)"""
        if not game_state:
            return
        
    # Vẽ nền
        self.draw_background()
            
    # Vẽ người chơi - SỬA LẠI MÀU SẮC
        for pid, player in game_state['players'].items():
            # Sửa màu sắc: người chơi hiện tại màu xanh, đối thủ màu đỏ
            if str(pid) == str(self.player_id):
                color = (0, 255, 0)  # Xanh lá - player hiện tại
            else:
                color = (255, 0, 0)  # Đỏ - đối thủ
                
            x, y = self._scale_position(player['x'], player['y'])
            radius = self._scale_value(20)
            pygame.draw.circle(self.screen, color, (int(x), int(y)), int(radius))
            
            # Vẽ tháp pháo
            end_x = x + self._scale_value(25) * math.cos(math.radians(player['angle']))
            end_y = y + self._scale_value(25) * math.sin(math.radians(player['angle']))
            pygame.draw.line(self.screen, color, (x, y), (end_x, end_y), int(self._scale_value(5)))
            
            # Vẽ thanh HP
            bar_width = self._scale_value(50)
            bar_height = self._scale_value(5)
            bar_x = x - self._scale_value(25)
            bar_y = y - self._scale_value(40)
            pygame.draw.rect(self.screen, (255,0,0), (bar_x, bar_y, bar_width, bar_height))
            pygame.draw.rect(self.screen, (0,255,0), (bar_x, bar_y, self._scale_value(player['hp']/2), bar_height))

    # Vẽ viên đạn
        for bullet in game_state['bullets']:
            x, y = self._scale_position(bullet['x'], bullet['y'])
            radius = self._scale_value(5)
            pygame.draw.circle(self.screen, (255, 255, 0), (int(x), int(y)), int(radius))
            
            # Vẽ vệt đạn
            trail_length = self._scale_value(10)
            start_x = x - trail_length * math.cos(math.radians(bullet['angle']))
            start_y = y - trail_length * math.sin(math.radians(bullet['angle']))
            pygame.draw.line(self.screen, (255, 200, 0), 
                            (start_x, start_y), 
                            (x, y), int(self._scale_value(2)))

    def draw_hud(self, ammo_count, max_ammo, reloading, reload_start_time, last_fire_time, game_over):
        """Vẽ HUD với thông tin game"""
    # Tạo nền bán trong suốt cho HUD
        hud_bg = pygame.Surface((self._scale_value(300), self._scale_value(120)), pygame.SRCALPHA)
        hud_bg.fill((0, 0, 0, 128))
        self.screen.blit(hud_bg, (self._scale_value(5), self._scale_value(5)))
        
    # Điều chỉnh kích thước phần tử HUD theo kích thước màn hình
        base_x = self._scale_value(15)
        base_y = self._scale_value(15)
        bar_width = self._scale_value(200)
        bar_height = self._scale_value(15)
        
    # Vẽ bộ đếm đạn
        ammo_color = (255, 255, 255)
        if ammo_count == 0:
            ammo_color = (255, 0, 0)
        elif ammo_count <= 3:
            ammo_color = (255, 165, 0)
            
        ammo_text = self.font.render(f"Ammo: {ammo_count}/{max_ammo}", True, ammo_color)
        self.screen.blit(ammo_text, (base_x, base_y))
        
    # Vẽ thông tin bản đồ trên HUD
        map_text = self.font.render(f"Map: {self.current_map_id + 1}", True, (200, 200, 100))
        self.screen.blit(map_text, (self.current_size[0] - self._scale_value(100), base_y))
        
    # Vẽ thanh chỉ báo thời gian hồi bắn
        fire_cooldown_percent = min(1.0, (time.time() - last_fire_time) / GameConstants.FIRE_COOLDOWN)
        pygame.draw.rect(self.screen, (100, 100, 100), (base_x, base_y + self._scale_value(35), bar_width, bar_height))
        pygame.draw.rect(self.screen, (0, 200, 0), (base_x, base_y + self._scale_value(35), bar_width * fire_cooldown_percent, bar_height))
        fire_text = self.font.render("Fire Cooldown", True, (255, 255, 255))
        self.screen.blit(fire_text, (base_x, base_y + self._scale_value(15)))
        
    # Vẽ chỉ báo nạp đạn
        if reloading:
            reload_progress = min(1.0, (time.time() - reload_start_time) / GameConstants.RELOAD_DURATION)
            pygame.draw.rect(self.screen, (100, 100, 100), (base_x, base_y + self._scale_value(75), bar_width, bar_height))
            pygame.draw.rect(self.screen, (0, 100, 255), (base_x, base_y + self._scale_value(75), bar_width * reload_progress, bar_height))
            
            # Hiển thị thời gian nạp còn lại
            time_left = GameConstants.RELOAD_DURATION - (time.time() - reload_start_time)
            reload_text = self.font.render(f"Reloading: {time_left:.1f}s", True, (255, 255, 255))
            self.screen.blit(reload_text, (base_x + bar_width + self._scale_value(10), base_y + self._scale_value(75)))
        else:
            # Hiển thị hướng dẫn nạp đạn khi hết đạn hoặc còn ít đạn
            if ammo_count == 0 and not game_over:
                reload_text = self.font.render("Press R to reload (7s)", True, (255, 255, 0))
                self.screen.blit(reload_text, (base_x, base_y + self._scale_value(55)))
            elif ammo_count <= 3 and not game_over:
                reload_text = self.font.render("Low ammo! Press R to reload", True, (255, 165, 0))
                self.screen.blit(reload_text, (base_x, base_y + self._scale_value(55)))

    def draw_game_over(self, winner_id, waiting_for_restart):
        """Vẽ màn hình game over"""
    # Overlay bán trong suốt
        overlay = pygame.Surface(self.current_size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        center_x, center_y = self._get_center()
        
    # Xác định văn bản hiển thị người chiến thắng
        if winner_id == self.player_id:
            winner_text = self.big_font.render("VICTORY!", True, (0, 255, 0))
        elif winner_id is None:
            winner_text = self.big_font.render("DRAW GAME!", True, (255, 255, 0))
        else:
            winner_text = self.big_font.render("DEFEAT!", True, (255, 0, 0))
        
        text_rect = winner_text.get_rect(center=(center_x, self._scale_value(250, False)))
        self.screen.blit(winner_text, text_rect)
        
    # Hiển thị thông tin bản đồ
        map_text = self.font.render(f"Map: {self.current_map_id + 1}", True, (200, 200, 100))
        map_rect = map_text.get_rect(center=(center_x, self._scale_value(300, False)))
        self.screen.blit(map_text, map_rect)
        
    # Hiển thị hướng dẫn khởi động lại
        if waiting_for_restart:
            restart_text = self.font.render("Waiting for other players...", True, (255, 255, 255))
        else:
            restart_text = self.font.render("Press T to play again", True, (255, 255, 255))
        
        restart_rect = restart_text.get_rect(center=(center_x, self._scale_value(350, False)))
        self.screen.blit(restart_text, restart_rect)

    def update_display(self):
        """Cập nhật màn hình"""
        pygame.display.flip()

    def cleanup(self):
        """Dọn dẹp pygame"""
        pygame.quit()