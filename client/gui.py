import pygame
import math
import time
import random
import os
import sys
from common.messages import GameConstants

# Optional UI helper: pygame_gui (if installed)
try:
    import pygame_gui
    HAVE_PYGAME_GUI = True
except Exception:
    pygame_gui = None
    HAVE_PYGAME_GUI = False

class ParticleSystem:
    """Hệ thống quản lý hiệu ứng particle"""
    def __init__(self):
        self.particles = []
        self.explosions = []
        self.trails = []
    
    def add_particle(self, x, y, color, velocity, lifetime=1.0, size=3, fade=True):
        self.particles.append({
            'x': x, 'y': y, 
            'color': color,
            'vx': velocity[0], 'vy': velocity[1],
            'lifetime': lifetime,
            'max_lifetime': lifetime,
            'size': size,
            'fade': fade
        })
    
    def add_explosion(self, x, y, size=1.0, color=None):
        self.explosions.append({
            'x': x, 'y': y,
            'size': size,
            'progress': 0.0,
            'max_size': 40 * size,
            'color': color or (255, 200, 100)
        })
    
    def add_trail(self, x, y, color, size=2, lifetime=0.5):
        self.trails.append({
            'x': x, 'y': y,
            'color': color,
            'lifetime': lifetime,
            'max_lifetime': lifetime,
            'size': size
        })
    
    def update(self, dt):
        # Update particles
        new_particles = []
        for p in self.particles:
            p['x'] += p['vx'] * dt * 60
            p['y'] += p['vy'] * dt * 60
            p['lifetime'] -= dt
            if p['lifetime'] > 0:
                new_particles.append(p)
        self.particles = new_particles
        
        # Update explosions
        new_explosions = []
        for e in self.explosions:
            e['progress'] += dt * 3
            if e['progress'] < 1.0:
                new_explosions.append(e)
        self.explosions = new_explosions
        
        # Update trails
        new_trails = []
        for t in self.trails:
            t['lifetime'] -= dt
            if t['lifetime'] > 0:
                new_trails.append(t)
        self.trails = new_trails
    
    def draw(self, screen):
        # Draw trails
        for t in self.trails:
            alpha = int(255 * (t['lifetime'] / t['max_lifetime']))
            size = int(t['size'] * (t['lifetime'] / t['max_lifetime']))
            if size < 1: size = 1
            
            color = list(t['color'])
            if len(color) == 3:
                color.append(alpha)
            
            surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (size, size), size)
            screen.blit(surf, (t['x']-size, t['y']-size))
        
        # Draw particles
        for p in self.particles:
            if p['fade']:
                alpha = int(255 * (p['lifetime'] / p['max_lifetime']))
            else:
                alpha = 255
                
            size = int(p['size'] * (p['lifetime'] / p['max_lifetime']))
            if size < 1: size = 1
            
            color = list(p['color'])
            if len(color) == 3:
                color.append(alpha)
            
            surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (size, size), size)
            screen.blit(surf, (p['x']-size, p['y']-size))
        
        # Draw explosions
        for e in self.explosions:
            progress = e['progress']
            size = e['max_size'] * (1 - (1 - progress) ** 2)
            alpha = int(255 * (1 - progress))
            
            # Main explosion
            color = list(e['color'])
            color.append(alpha)
            surf = pygame.Surface((int(size*2), int(size*2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (int(size), int(size)), int(size))
            
            # Shockwave
            wave_size = size * 1.3
            wave_alpha = int(150 * (1 - progress))
            wave_color = (min(255, e['color'][0] + 50), 
                         min(255, e['color'][1] + 30), 
                         max(0, e['color'][2] - 50), 
                         wave_alpha)
            pygame.draw.circle(surf, wave_color, (int(size), int(size)), int(wave_size), 3)
            
            screen.blit(surf, (e['x']-size, e['y']-size))


class GameRenderer:
    def __init__(self, username):
        self.player_name = username
        self.player_id = None
        self.screen = None
        self.font = None
        self.big_font = None
        self.original_width = GameConstants.SCREEN_WIDTH
        self.original_height = GameConstants.SCREEN_HEIGHT
        self.fullscreen = False
        self.backgrounds = []
        self.current_background = None
        self.scaled_background = None
        self.current_map_id = 0
        self.map_initialized = False
        
        # Particle system
        self.particles = ParticleSystem()
        
        # HP display cache
        self._hp_display = {}
        
        # Animation states
        self.screen_shake = 0
        self.pulse_animation = 0
        
        # Lấy đường dẫn gốc của dự án
        if sys.path[0]:
            self.project_root = sys.path[0]
        else:
            self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Premium theme management
        self.THEMES = {
            'Cyber Warfare': {
                'bg_top': (10, 15, 25),
                'bg_bottom': (5, 8, 15),
                'card': (18, 25, 40),
                'card_border': (40, 60, 100),
                'accent': (0, 200, 255),
                'accent_dark': (0, 150, 200),
                'player': (0, 255, 180),
                'player_dark': (0, 180, 130),
                'enemy': (255, 80, 80),
                'enemy_dark': (200, 50, 50),
                'hud_bg': (8, 12, 20, 220),
                'hud_border': (30, 45, 70),
                'hud_text': (220, 240, 255),
                'muted': (100, 120, 150),
                'white': (255,255,255),
                'green': (0, 255, 150),
                'yellow': (255, 220, 60),
                'red': (255, 70, 70),
                'shadow': (5, 8, 12),
                'energy': (0, 255, 255),
                'metal': (180, 200, 220)
            },
            'Desert Storm': {
                'bg_top': (40, 30, 20),
                'bg_bottom': (25, 18, 10),
                'card': (50, 40, 30),
                'card_border': (90, 70, 40),
                'accent': (255, 180, 60),
                'accent_dark': (220, 150, 40),
                'player': (60, 200, 100),
                'player_dark': (40, 150, 70),
                'enemy': (220, 80, 60),
                'enemy_dark': (180, 50, 40),
                'hud_bg': (35, 25, 15, 220),
                'hud_border': (80, 60, 35),
                'hud_text': (240, 230, 200),
                'muted': (150, 130, 100),
                'white': (255,255,255),
                'green': (80, 220, 120),
                'yellow': (255, 200, 60),
                'red': (220, 80, 60),
                'shadow': (20, 15, 8),
                'energy': (255, 200, 50),
                'metal': (200, 180, 140)
            },
            'Neon Night': {
                'bg_top': (15, 5, 25),
                'bg_bottom': (8, 2, 15),
                'card': (25, 10, 35),
                'card_border': (80, 20, 120),
                'accent': (180, 0, 255),
                'accent_dark': (140, 0, 200),
                'player': (0, 255, 100),
                'player_dark': (0, 180, 70),
                'enemy': (255, 20, 100),
                'enemy_dark': (200, 10, 70),
                'hud_bg': (20, 5, 25, 220),
                'hud_border': (60, 15, 80),
                'hud_text': (240, 220, 255),
                'muted': (120, 80, 150),
                'white': (255,255,255),
                'green': (0, 255, 120),
                'yellow': (255, 220, 0),
                'red': (255, 40, 80),
                'shadow': (10, 2, 15),
                'energy': (180, 0, 255),
                'metal': (200, 180, 220)
            }
        }

        # Enable synchronized random theme selection (based on map id)
        self.theme_name = 'random'
        self.random_theme_sync = True
        self.set_theme(self.theme_name)

    def set_theme(self, name):
        """Chọn theme theo tên"""
        if name in self.THEMES:
            self.colors = self.THEMES[name]
            self.theme_name = name
            self.random_theme_sync = False
        else:
            keys = list(self.THEMES.keys())
            # Deterministic pick based on current map id for cross-client sync
            map_id = self.current_map_id if isinstance(getattr(self, 'current_map_id', 0), int) else 0
            idx = (map_id * 7 + 3) % max(1, len(keys))
            picked = keys[idx]
            self.colors = self.THEMES[picked]
            self.theme_name = 'random'
            self.random_theme_sync = True

    def set_player_id(self, player_id):
        """Gán player ID sau khi nhận từ server"""
        self.player_id = player_id
        pygame.display.set_caption(f"Fire Tank - {self.player_name} (Player {self.player_id})")
        self.scaled_background = None

    def initialize(self):
        """Khởi tạo pygame và font"""
        pygame.init()
        self.screen = pygame.display.set_mode(
            (self.original_width, self.original_height), 
            pygame.RESIZABLE | pygame.SCALED
        )
        pygame.display.set_caption(f"Fire Tank - Player {self.player_id}")
        
        # Load premium fonts
        try:
            font_path = os.path.join(self.project_root, "ui", "fonts")
            if os.path.exists(os.path.join(font_path, "orbitron.ttf")):
                self.font = pygame.font.Font(os.path.join(font_path, "orbitron.ttf"), 24)
                self.small_font = pygame.font.Font(os.path.join(font_path, "orbitron.ttf"), 16)
                self.big_font = pygame.font.Font(os.path.join(font_path, "orbitron.ttf"), 48)
                self.title_font = pygame.font.Font(os.path.join(font_path, "orbitron.ttf"), 64)
            else:
                preferred_fonts = ["Arial Black", "Verdana", "Segoe UI"]
                self.font = pygame.font.SysFont(preferred_fonts, 24)
                self.small_font = pygame.font.SysFont(preferred_fonts, 16)
                self.big_font = pygame.font.SysFont(preferred_fonts, 48)
                self.title_font = pygame.font.SysFont(preferred_fonts, 64)
        except:
            self.font = pygame.font.Font(None, 24)
            self.small_font = pygame.font.Font(None, 16)
            self.big_font = pygame.font.Font(None, 48)
            self.title_font = pygame.font.Font(None, 64)

        self.load_backgrounds()
        self.set_map(0)
        
        # Load logo
        try:
            logo_path = os.path.join(self.project_root, "ui", "logo.png")
            if os.path.exists(logo_path):
                self.logo = pygame.image.load(logo_path).convert_alpha()
            else:
                self.logo = None
        except Exception:
            self.logo = None

    def add_screen_shake(self, intensity=5):
        """Thêm hiệu ứng rung màn hình"""
        self.screen_shake = intensity

    def update_animations(self, dt):
        """Cập nhật tất cả animations"""
        self.pulse_animation = (self.pulse_animation + dt * 2) % 1
        
        # Update screen shake
        if self.screen_shake > 0:
            self.screen_shake -= dt * 10
            if self.screen_shake < 0:
                self.screen_shake = 0
        
        # Update particles
        self.particles.update(dt)

    def _draw_premium_bg(self):
        """Vẽ background cao cấp với hiệu ứng parallax"""
        self._draw_gradient_bg(self.colors['bg_top'], self.colors['bg_bottom'])
        
        w, h = self.original_width, self.original_height
        time_val = time.time()
        
        # Vẽ các ngôi sao
        for i in range(100):
            x = (i * 97) % w
            y = (i * 63) % h
            size = 0.5 + (i % 4) * 0.5
            brightness = int(100 + 155 * abs(math.sin(time_val * 0.3 + i * 0.5)))
            color = (brightness, brightness, brightness)
            pygame.draw.circle(self.screen, color, (int(x), int(y)), max(1, int(round(size))))
        
        # Vẽ grid tinh tế
        for i in range(0, w, 60):
            alpha = int(15 + 10 * math.sin(time_val * 0.2 + i * 0.01))
            pygame.draw.line(self.screen, 
                           (*self.colors['accent'][:3], alpha), 
                           (i, 0), (i, h), 1)
        for i in range(0, h, 60):
            alpha = int(15 + 10 * math.sin(time_val * 0.2 + i * 0.01))
            pygame.draw.line(self.screen, 
                           (*self.colors['accent'][:3], alpha), 
                           (0, i), (w, i), 1)

    def _draw_gradient_bg(self, top_color, bottom_color):
        """Vẽ gradient background"""
        w, h = self.original_width, self.original_height
        grad = pygame.Surface((1, h)).convert_alpha()
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
            g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
            b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
            grad.set_at((0, y), (r, g, b))
        grad = pygame.transform.scale(grad, (w, h))
        self.screen.blit(grad, (0, 0))

    def _draw_glowing_card(self, rect, color, glow_size=10, radius=10):
        """Vẽ thẻ với hiệu ứng glow"""
        x, y, w, h = rect
        glow_size = int(max(0, round(glow_size)))
        radius = int(round(radius))
        glow_surf = pygame.Surface((w + glow_size*2, h + glow_size*2), pygame.SRCALPHA)
        
        for i in range(glow_size, 0, -1):
            alpha = 80 - (i * 80 // glow_size)
            glow_color = (*color[:3], alpha)
            pygame.draw.rect(glow_surf, glow_color, 
                           (glow_size-i, glow_size-i, w+i*2, h+i*2), 
                           border_radius=radius+i)
        
        self.screen.blit(glow_surf, (x - glow_size, y - glow_size))

    def _draw_card(self, rect, color, border_color=None, radius=10):
        """Vẽ thẻ với bo góc"""
        x, y, w, h = rect
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, color, (0, 0, w, h), border_radius=radius)
        if border_color:
            pygame.draw.rect(s, border_color, (0, 0, w, h), 2, border_radius=radius)
        self.screen.blit(s, (x, y))

    def _draw_premium_button(self, rect, text, hover=False, pulse=0):
        """Vẽ nút cao cấp"""
        x, y, w, h = rect
        
        if hover:
            base_color = self.colors['accent']
            text_color = self.colors['card']
            glow_strength = 10
        else:
            base_color = self.colors['card_border']
            text_color = self.colors['hud_text']
            glow_strength = 3 + 2 * math.sin(pulse * math.pi * 2)
        
        if glow_strength > 0:
            self._draw_glowing_card((x-2, y-2, w+4, h+4), self.colors['accent'], glow_strength, 10)
        
        self._draw_card((x, y, w, h), color=base_color, border_color=self.colors['accent'], radius=10)
        
        text_surf = self.font.render(text, True, text_color)
        self.screen.blit(text_surf, text_surf.get_rect(center=rect.center))
        
        if hover:
            highlight = pygame.Surface((w, h), pygame.SRCALPHA)
            points = [(0, 0), (w//2, 0), (0, h//2)]
            pygame.draw.polygon(highlight, (255, 255, 255, 50), points)
            self.screen.blit(highlight, (x, y))

    def _draw_input_box(self, rect, text, active=False, password=False):
        """Vẽ ô input cao cấp"""
        x, y, w, h = rect
        
        border_color = self.colors['accent'] if active else self.colors['card_border']
        self._draw_card((x, y, w, h), color=self.colors['card'], border_color=border_color, radius=8)
        
        if active:
            self._draw_glowing_card((x-2, y-2, w+4, h+4), self.colors['accent'], 3, 8)
        
        display_text = text
        if password:
            display_text = '*' * len(text)
        
        if display_text:
            text_surf = self.font.render(display_text, True, self.colors['hud_text'])
        else:
            text_surf = self.font.render("", True, self.colors['muted'])
        
        text_rect = text_surf.get_rect(midleft=(x + 12, y + h//2))
        
        max_width = w - 24
        if text_surf.get_width() > max_width:
            temp_surf = pygame.Surface((max_width, h-8), pygame.SRCALPHA)
            temp_surf.blit(text_surf, (0, 0))
            self.screen.blit(temp_surf, (x + 12, y + 4))
        else:
            self.screen.blit(text_surf, text_rect)
        
        if active and time.time() % 1 > 0.5:
            cursor_x = text_rect.left + text_surf.get_width() + 2
            pygame.draw.line(self.screen, self.colors['accent'], 
                           (cursor_x, y+8), (cursor_x, y+h-8), 2)

    def show_auth_menu(self):
        """Hiển thị màn hình chọn Login hoặc Register"""
        clock = pygame.time.Clock()
        cx, cy = self._get_center()
        w, h = 500, 200
        left, top = cx - w//2, cy - h//2
        
        pulse, hover_login, hover_register = 0, False, False
        running, choice = True, None
        
        while running and choice is None:
            dt = clock.tick(60) / 1000.0
            pulse = (pulse + dt * 2) % 1
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    login_rect = pygame.Rect(left + 50, top + 100, 180, 60)
                    reg_rect = pygame.Rect(left + 270, top + 100, 180, 60)
                    if login_rect.collidepoint(mx, my):
                        choice = 'login'
                    if reg_rect.collidepoint(mx, my):
                        choice = 'register'

            mx, my = pygame.mouse.get_pos()
            login_rect = pygame.Rect(left + 50, top + 100, 180, 60)
            reg_rect = pygame.Rect(left + 270, top + 100, 180, 60)
            hover_login = login_rect.collidepoint(mx, my)
            hover_register = reg_rect.collidepoint(mx, my)

            # Draw
            self._draw_premium_bg()
            self._draw_glowing_card((left-5, top-5, w+10, h+10), self.colors['accent'], 8, 15)
            self._draw_card((left, top, w, h), color=self.colors['card'], border_color=self.colors['accent'], radius=15)

            # Title
            title_glow = self.title_font.render("FIRE TANK", True, self.colors['accent'])
            title = self.title_font.render("FIRE TANK", True, self.colors['white'])
            for offset in [(2,2), (-2,2), (2,-2), (-2,-2)]:
                self.screen.blit(title_glow, title_glow.get_rect(center=(cx+offset[0], top+40+offset[1])))
            self.screen.blit(title, title.get_rect(center=(cx, top+40)))

            # Buttons
            self._draw_premium_button(login_rect, "LOGIN", hover_login, pulse)
            self._draw_premium_button(reg_rect, "REGISTER", hover_register, pulse)

            # Subtitle
            subtitle = self.small_font.render("CHOOSE YOUR PATH, COMMANDER", True, self.colors['muted'])
            self.screen.blit(subtitle, subtitle.get_rect(center=(cx, top+80)))

            pygame.display.flip()

        return choice

    def show_login_screen(self):
        """Hiển thị màn hình đăng nhập/đăng ký"""
        selection = None
        
        while True:
            selection = self.show_auth_menu()
            if selection is None:
                return None

            if HAVE_PYGAME_GUI and self.screen is not None:
                try:
                    if selection == 'register':
                        res = self._show_register_with_pygame_gui()
                    else:
                        res = self._show_login_with_pygame_gui()
                except Exception:
                    res = self._show_login_page_custom() if selection == 'login' else self._show_register_page_custom()
            else:
                if selection == 'register':
                    res = self._show_register_page_custom()
                else:
                    res = self._show_login_page_custom()

            if res is None:
                return None
            if isinstance(res, dict) and res.get('action') == 'back':
                continue
            return res

    def _show_login_page_custom(self):
        """Hiển thị trang đăng nhập custom"""
        host, username, password = '', '', ''
        active = 0
        clock = pygame.time.Clock()
        running = True
        
        while running:
            dt = clock.tick(60) / 1000.0
            self.update_animations(dt)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return {'action': 'back'}
                    if event.key == pygame.K_TAB:
                        active = (active + 1) % 3
                    elif event.key == pygame.K_RETURN:
                        if username and password:
                            running = False
                    elif event.key == pygame.K_BACKSPACE:
                        if active == 0: host = host[:-1]
                        elif active == 1: username = username[:-1]
                        elif active == 2: password = password[:-1]
                    else:
                        ch = event.unicode
                        if ch:
                            if active == 0: host += ch
                            elif active == 1: username += ch
                            elif active == 2: password += ch
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    cx, cy = self._get_center()
                    start_x = cx - 200
                    y0 = 180
                    boxes = [
                        pygame.Rect(start_x, y0, 400, 40),
                        pygame.Rect(start_x, y0 + 60, 400, 40),
                        pygame.Rect(start_x, y0 + 120, 400, 40)
                    ]
                    for i, r in enumerate(boxes):
                        if r.collidepoint(mx, my):
                            active = i
                    
                    back_rect = pygame.Rect(start_x - 100, y0 - 48, 80, 30)
                    if back_rect.collidepoint(mx, my):
                        return {'action': 'back'}

            # Draw
            self._draw_premium_bg()
            cx, cy = self._get_center()
            
            # Main card
            self._draw_glowing_card((cx-240, 60, 480, 400), self.colors['accent'], 10, 20)
            self._draw_card((cx-235, 65, 470, 390), color=self.colors['card'], border_color=self.colors['accent'], radius=20)
            
            # Title
            title = self.big_font.render("LOGIN TO BATTLE", True, self.colors['accent'])
            self.screen.blit(title, title.get_rect(center=(cx, 100)))
            
            # Input fields
            start_x = cx - 200
            y0 = 180
            
            # Host input
            host_rect = pygame.Rect(start_x, y0, 400, 40)
            self._draw_input_box(host_rect, host, active == 0)
            host_label = self.small_font.render("SERVER HOST (localhost if empty)", True, self.colors['hud_text'])
            self.screen.blit(host_label, (start_x, y0 - 20))
            
            # Username input
            user_rect = pygame.Rect(start_x, y0 + 60, 400, 40)
            self._draw_input_box(user_rect, username, active == 1)
            user_label = self.small_font.render("USERNAME", True, self.colors['hud_text'])
            self.screen.blit(user_label, (start_x, y0 + 40))
            
            # Password input
            pass_rect = pygame.Rect(start_x, y0 + 120, 400, 40)
            self._draw_input_box(pass_rect, password, active == 2, password=True)
            pass_label = self.small_font.render("PASSWORD", True, self.colors['hud_text'])
            self.screen.blit(pass_label, (start_x, y0 + 100))
            
            # Back button
            back_rect = pygame.Rect(start_x - 100, y0 - 48, 80, 30)
            self._draw_premium_button(back_rect, "BACK", False, self.pulse_animation)
            
            # Instructions
            info = self.small_font.render("Press ENTER to submit • TAB to switch fields", True, self.colors['muted'])
            self.screen.blit(info, info.get_rect(center=(cx, y0 + 190)))
            
            pygame.display.flip()

        if not host.strip():
            host = 'localhost'
        return {
            'host': host.strip(),
            'type': 'login',
            'username': username.strip(),
            'password': password,
            'name': None
        }

    def _show_register_page_custom(self):
        """Hiển thị trang đăng ký custom"""
        host, username, password, name = '', '', '', ''
        active = 0
        clock = pygame.time.Clock()
        running = True
        
        while running:
            dt = clock.tick(60) / 1000.0
            self.update_animations(dt)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return {'action': 'back'}
                    if event.key == pygame.K_TAB:
                        active = (active + 1) % 4
                    elif event.key == pygame.K_RETURN:
                        if username and password and name:
                            running = False
                    elif event.key == pygame.K_BACKSPACE:
                        if active == 0: host = host[:-1]
                        elif active == 1: username = username[:-1]
                        elif active == 2: password = password[:-1]
                        elif active == 3: name = name[:-1]
                    else:
                        ch = event.unicode
                        if ch:
                            if active == 0: host += ch
                            elif active == 1: username += ch
                            elif active == 2: password += ch
                            elif active == 3: name += ch
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    cx, cy = self._get_center()
                    start_x = cx - 200
                    y0 = 160
                    boxes = [
                        pygame.Rect(start_x, y0, 400, 40),
                        pygame.Rect(start_x, y0 + 60, 400, 40),
                        pygame.Rect(start_x, y0 + 120, 400, 40),
                        pygame.Rect(start_x, y0 + 180, 400, 40)
                    ]
                    for i, r in enumerate(boxes):
                        if r.collidepoint(mx, my):
                            active = i
                    
                    back_rect = pygame.Rect(start_x - 100, y0 - 48, 80, 30)
                    if back_rect.collidepoint(mx, my):
                        return {'action': 'back'}

            # Draw
            self._draw_premium_bg()
            cx, cy = self._get_center()
            
            # Main card
            self._draw_glowing_card((cx-240, 40, 480, 450), self.colors['accent'], 10, 20)
            self._draw_card((cx-235, 45, 470, 440), color=self.colors['card'], border_color=self.colors['accent'], radius=20)
            
            # Title
            title = self.big_font.render("JOIN THE BATTLE", True, self.colors['accent'])
            self.screen.blit(title, title.get_rect(center=(cx, 80)))
            
            # Input fields
            start_x = cx - 200
            y0 = 160
            
            fields = [
                (host, "SERVER HOST (localhost if empty)", False),
                (username, "USERNAME", False),
                (password, "PASSWORD", True),
                (name, "DISPLAY NAME", False)
            ]
            
            for i, (text, label_text, is_password) in enumerate(fields):
                rect = pygame.Rect(start_x, y0 + i * 60, 400, 40)
                self._draw_input_box(rect, text, active == i, is_password)
                label = self.small_font.render(label_text, True, self.colors['hud_text'])
                self.screen.blit(label, (start_x, y0 + i * 60 - 20))
            
            # Back button
            back_rect = pygame.Rect(start_x - 100, y0 - 48, 80, 30)
            self._draw_premium_button(back_rect, "BACK", False, self.pulse_animation)
            
            # Instructions
            info = self.small_font.render("Press ENTER to register • TAB to switch fields", True, self.colors['muted'])
            self.screen.blit(info, info.get_rect(center=(cx, y0 + 250)))
            
            pygame.display.flip()

        if not host.strip():
            host = 'localhost'
        return {
            'host': host.strip(),
            'type': 'register',
            'username': username.strip(),
            'password': password,
            'name': name.strip() if name.strip() else None
        }

    def _show_login_with_pygame_gui(self):
        """Hiển thị đăng nhập với pygame_gui"""
        if not HAVE_PYGAME_GUI:
            return self._show_login_page_custom()
        
        # Implementation với pygame_gui
        # ... (giữ nguyên implementation cũ)
        return self._show_login_page_custom()

    def _show_register_with_pygame_gui(self):
        """Hiển thị đăng ký với pygame_gui"""
        if not HAVE_PYGAME_GUI:
            return self._show_register_page_custom()
        
        # Implementation với pygame_gui
        # ... (giữ nguyên implementation cũ)
        return self._show_register_page_custom()

    def load_backgrounds(self):
        """Load background images"""
        background_dir = os.path.join(self.project_root, "ui")
        background_files = ["map1.png", "map2.png", "map3.png"]
        
        for bg_file in background_files:
            bg_path = os.path.join(background_dir, bg_file)
            if os.path.exists(bg_path):
                try:
                    img = pygame.image.load(bg_path)
                    try:
                        background = img.convert_alpha()
                    except Exception:
                        background = img.convert()
                    self.backgrounds.append(background)
                except Exception as e:
                    print(f"Error loading {bg_file}: {e}")
                    self.create_default_background(background_files.index(bg_file))
            else:
                self.create_default_background(background_files.index(bg_file))
        
        while len(self.backgrounds) < 3:
            self.create_default_background(len(self.backgrounds))

    def create_default_background(self, map_id):
        """Tạo background mặc định"""
        colors = [
            (30, 40, 60),   # Blue
            (40, 60, 30),   # Green  
            (60, 30, 50)    # Purple
        ]
        
        color = colors[map_id] if map_id < len(colors) else (50, 50, 50)
        bg = pygame.Surface((self.original_width, self.original_height))
        bg.fill(color)
        
        # Add pattern
        for i in range(0, self.original_width, 50):
            for j in range(0, self.original_height, 50):
                if map_id == 0:
                    pygame.draw.circle(bg, (color[0] + 20, color[1] + 20, color[2] + 20), 
                                     (i + 25, j + 25), 4)
                elif map_id == 1:
                    pygame.draw.rect(bg, (color[0] + 20, color[1] + 20, color[2] + 20), 
                                     (i + 20, j + 20, 10, 10))
                else:
                    points = [(i + 25, j + 15), (i + 35, j + 25), 
                              (i + 25, j + 35), (i + 15, j + 25)]
                    pygame.draw.polygon(bg, (color[0] + 20, color[1] + 20, color[2] + 20), points)
        
        font = pygame.font.SysFont(None, 48)
        text = font.render(f"MAP {map_id + 1}", True, self.colors['white'])
        text_rect = text.get_rect(center=(self.original_width // 2, self.original_height // 2))
        bg.blit(text, text_rect)
        
        self.backgrounds.append(bg)

    def set_map(self, map_id):
        """Thiết lập map"""
        try:
            map_id = int(map_id)
        except Exception:
            map_id = 0

        if 0 <= map_id < len(self.backgrounds):
            self.current_map_id = map_id
            self.current_background = self.backgrounds[map_id]
            self.map_initialized = True
        else:
            if self.backgrounds:
                self.current_map_id = 0
                self.current_background = self.backgrounds[0]
                self.map_initialized = True

        if self.current_background:
            self.scaled_background = pygame.transform.scale(
                self.current_background, 
                (self.original_width, self.original_height)
            )
        
        # Refresh theme if in synchronized random mode
        if getattr(self, 'random_theme_sync', False):
            self.set_theme('random')
    
    def get_current_map_id(self):
        """Trả về ID map hiện tại"""
        return self.current_map_id

    def toggle_fullscreen(self):
        """Chuyển đổi chế độ fullscreen"""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode(
                (self.original_width, self.original_height), 
                pygame.FULLSCREEN | pygame.SCALED
            )
        else:
            self.screen = pygame.display.set_mode(
                (self.original_width, self.original_height), 
                pygame.RESIZABLE | pygame.SCALED
            )

    def _get_center(self):
        return self.original_width // 2, self.original_height // 2

    def draw_background(self):
        """Vẽ background"""
        if self.scaled_background:
            # Apply screen shake
            amp = int(self.screen_shake)
            shake_x = random.randint(-amp, amp) if amp > 0 else 0
            shake_y = random.randint(-amp, amp) if amp > 0 else 0
            self.screen.blit(self.scaled_background, (shake_x, shake_y))
        else:
            self._draw_premium_bg()

    def draw_waiting_screen(self, game_state, ready, waiting_for_players):
        """Vẽ màn hình chờ"""
        self.draw_background()
        
        # Overlay
        overlay = pygame.Surface((self.original_width, self.original_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        cx, cy = self._get_center()

        # Title
        title_text = self.title_font.render("FIRE TANK", True, self.colors['accent'])
        title_rect = title_text.get_rect(center=(cx, 100))
        self.screen.blit(title_text, title_rect)

        # Player ID
        id_surf = self.font.render(f"PLAYER ID: {self.player_id}", True, self.colors['hud_text'])
        self.screen.blit(id_surf, id_surf.get_rect(center=(cx, 160)))

        # Status
        t = time.time()
        dots = int((t * 2) % 4)
        dot_str = "." * dots
        if waiting_for_players:
            status_str = f"WAITING FOR PLAYERS{dot_str}"
            status_color = self.colors['accent']
        elif ready:
            status_str = "READY - WAITING FOR OTHERS"
            status_color = self.colors['player']
        else:
            status_str = "PRESS SPACE TO READY UP"
            status_color = self.colors['accent_dark']
        status_surf = self.font.render(status_str, True, status_color)
        self.screen.blit(status_surf, status_surf.get_rect(center=(cx, 200)))

        # Map preview
        thumb_w, thumb_h = 300, 180
        thumb_x, thumb_y = cx - 350, 240
        if self.current_background:
            thumb = pygame.transform.smoothscale(self.current_background, (thumb_w, thumb_h))
            self._draw_card((thumb_x - 10, thumb_y - 10, thumb_w + 20, thumb_h + 20), 
                          color=self.colors['card'], border_color=self.colors['card_border'])
            self.screen.blit(thumb, (thumb_x, thumb_y))
            map_label = self.small_font.render(f"BATTLEFIELD {self.current_map_id + 1}", True, self.colors['accent'])
            self.screen.blit(map_label, (thumb_x + thumb_w//2 - map_label.get_width()//2, thumb_y + thumb_h + 10))

        # Players list
        players = []
        if game_state and isinstance(game_state, dict) and 'players' in game_state:
            for pid, pdata in game_state['players'].items():
                display = pdata.get('name') if isinstance(pdata, dict) and pdata.get('name') else f"Player {pid}"
                is_ready = bool(pdata.get('ready')) if isinstance(pdata, dict) else False
                players.append((str(pid), display, is_ready))

        # Draw player avatars
        icon_size = 50
        gap = 20
        total_width = len(players) * icon_size + max(0, len(players)-1) * gap
        start_x = thumb_x + (thumb_w - total_width) // 2 if total_width > 0 else thumb_x
        py = thumb_y + thumb_h + 60
        
        for i, (pid, name, is_ready) in enumerate(players):
            x = start_x + i * (icon_size + gap)
            
            # Avatar
            is_self = str(pid) == str(self.player_id)
            bg_color = self.colors['player'] if is_self else self.colors['card_border']
            pygame.draw.circle(self.screen, bg_color, (x + icon_size//2, py), icon_size//2)
            
            # Initial
            letter = name[0].upper() if name else '?'
            letter_surf = self.small_font.render(letter, True, self.colors['card'])
            self.screen.blit(letter_surf, letter_surf.get_rect(center=(x + icon_size//2, py)))
            
            # Ready indicator
            tick_color = self.colors['player'] if is_ready else self.colors['muted']
            pygame.draw.circle(self.screen, tick_color, (x + icon_size - 8, py + icon_size//2 - 8), 6)
            
            # Name
            name_surf = self.small_font.render(name, True, self.colors['hud_text'])
            self.screen.blit(name_surf, (x + (icon_size - name_surf.get_width())//2, py + icon_size//2 + 10))

        # Connection progress
        total_needed = GameConstants.MAX_PLAYERS
        connected = max(0, len(players))
        bar_w, bar_h = 400, 20
        bar_x, bar_y = cx - bar_w // 2, py + 80
        
        self._draw_card((bar_x, bar_y, bar_w, bar_h), color=self.colors['card_border'], radius=10)
        
        if total_needed > 0:
            fill_w = int(bar_w * (connected / total_needed))
            if fill_w > 0:
                pygame.draw.rect(self.screen, self.colors['accent'], 
                               (bar_x, bar_y, fill_w, bar_h), border_radius=10)
        
        pct_text = self.small_font.render(f"{connected}/{total_needed} COMBATANTS READY", True, self.colors['hud_text'])
        self.screen.blit(pct_text, pct_text.get_rect(center=(cx, bar_y + bar_h//2)))

        # Controls
        controls_x = cx + 200
        controls_y = 240
        heading = self.font.render("CONTROLS", True, self.colors['accent'])
        self.screen.blit(heading, (controls_x - heading.get_width()//2, controls_y))
        
        controls = [
            "SPACE - Ready Up",
            "ARROW KEYS - Move & Aim",
            "SPACE - Fire Weapon", 
            "R - Reload Ammo",
            "T - Restart Match",
            "F - Toggle Fullscreen"
        ]
        
        for i, control in enumerate(controls):
            text = self.small_font.render(control, True, self.colors['hud_text'])
            self.screen.blit(text, (controls_x - 120, controls_y + 40 + i * 25))

    def draw_tank(self, x, y, angle, is_player):
        """Vẽ xe tăng bằng các khối hình học"""
        tank_size = 40
        tank_width = tank_size
        tank_height = tank_size * 0.6
        
        # Màu sắc: xanh cho player, đỏ cho enemy
        base_color = self.colors['player'] if is_player else self.colors['enemy']
        dark_color = self.colors['player_dark'] if is_player else self.colors['enemy_dark']
        highlight_color = self.colors['accent'] if is_player else self.colors['accent_dark']
        
        # Vẽ thân xe (hình chữ nhật bo góc)
        body_rect = pygame.Rect(
            int(x - tank_width/2), int(y - tank_height/2),
            int(tank_width), int(tank_height)
        )
        pygame.draw.rect(self.screen, base_color, body_rect, border_radius=8)
        pygame.draw.rect(self.screen, dark_color, body_rect, 2, border_radius=8)
        
        # Vẽ tháp pháo (hình tròn)
        turret_radius = tank_size * 0.25
        pygame.draw.circle(self.screen, base_color, (int(x), int(y)), int(turret_radius))
        pygame.draw.circle(self.screen, dark_color, (int(x), int(y)), int(turret_radius), 2)
        
        # Vẽ nòng súng
        barrel_length = tank_size * 0.8
        end_x = x + barrel_length * math.cos(math.radians(angle))
        end_y = y + barrel_length * math.sin(math.radians(angle))
        
        # Vẽ nòng súng dày hơn với gradient màu
        barrel_width = tank_size * 0.15
        barrel_vector = pygame.Vector2(barrel_length * math.cos(math.radians(angle)), 
                                     barrel_length * math.sin(math.radians(angle)))
        perpendicular = pygame.Vector2(-barrel_vector.y, barrel_vector.x).normalize() * (barrel_width/2)
        barrel_points = [
            (x + perpendicular.x, y + perpendicular.y),
            (x - perpendicular.x, y - perpendicular.y),
            (end_x - perpendicular.x, end_y - perpendicular.y),
            (end_x + perpendicular.x, end_y + perpendicular.y)
        ]
        pygame.draw.polygon(self.screen, dark_color, barrel_points)
        
        # Vẽ viền sáng cho nòng súng
        pygame.draw.polygon(self.screen, highlight_color, barrel_points, 1)
        
        # Vẽ các chi tiết trang trí trên thân xe
        detail_color = highlight_color
        # Vẽ đường kẻ ngang
        pygame.draw.line(self.screen, detail_color, 
                        (x - tank_width/3, y - tank_height/4),
                        (x + tank_width/3, y - tank_height/4), 2)
        pygame.draw.line(self.screen, detail_color, 
                        (x - tank_width/3, y + tank_height/4),
                        (x + tank_width/3, y + tank_height/4), 2)
        
        # Vẽ logo nhỏ trên tháp pháo
        logo_color = self.colors['accent'] if is_player else self.colors['muted']
        pygame.draw.circle(self.screen, logo_color, (int(x), int(y)), int(turret_radius/2))
        pygame.draw.circle(self.screen, dark_color, (int(x), int(y)), int(turret_radius/2), 1)

    def draw_game_state(self, game_state):
        """Vẽ trạng thái game"""
        if not game_state:
            return
        
        self.draw_background()
        self.particles.draw(self.screen)
        
        # Vẽ tank và đạn
        for pid, player in game_state['players'].items():
            x, y = player['x'], player['y']
            angle = player['angle']
            is_player = (str(pid) == str(self.player_id))
            
            self.draw_tank(x, y, angle, is_player)
            self._draw_health_bar(x, y, player, is_player)
        
        for bullet in game_state['bullets']:
            x, y = bullet['x'], bullet['y']
            self._draw_bullet(x, y)

    def _draw_health_bar(self, x, y, player, is_player):
        """Vẽ thanh máu"""
        actual_hp = max(0, int(player.get('hp', 0)))
        hp_percent = max(0.0, min(1.0, actual_hp / max(1, GameConstants.PLAYER_HP)))
        
        bar_w, bar_h = 120, 16
        bar_x, bar_y = x - bar_w//2, y - 65
        
        # Background
        self._draw_card((bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), 
                      color=self.colors['card_border'], radius=8)
        
        # Fill
        if hp_percent > 0:
            fill_w = max(8, int(bar_w * hp_percent))
            
            # Color: player uses gradient, enemy always red
            if is_player:
                if hp_percent > 0.6:
                    color = self.colors['green']
                elif hp_percent > 0.3:
                    color = self.colors['yellow']
                else:
                    color = self.colors['red']
            else:
                color = self.colors['red']
            
            pygame.draw.rect(self.screen, color, 
                           (bar_x, bar_y, fill_w, bar_h), border_radius=8)
            
            # Highlight
            highlight = pygame.Surface((fill_w, bar_h//3), pygame.SRCALPHA)
            highlight.fill((255, 255, 255, 80))
            self.screen.blit(highlight, (bar_x, bar_y))
        
        # Border
        pygame.draw.rect(self.screen, self.colors['accent'], 
                        (bar_x, bar_y, bar_w, bar_h), 2, border_radius=8)
        
        # Text
        hp_text = f"{int(hp_percent * 100)}%"
        text_surf = self.small_font.render(hp_text, True, self.colors['hud_text'])
        self.screen.blit(text_surf, (bar_x + bar_w//2 - text_surf.get_width()//2, 
                                   bar_y + bar_h//2 - text_surf.get_height()//2))
        
        # Name
        name = player.get('name', f'Player {player.get("id", "")}')
        name_color = self.colors['player'] if is_player else self.colors['hud_text']
        name_surf = self.small_font.render(name, True, name_color)
        name_rect = name_surf.get_rect(center=(x, bar_y - 15))
        self.screen.blit(name_surf, name_rect)

    def _draw_bullet(self, x, y):
        """Vẽ đạn"""
        radius = 6
        # Only draw a minimal bullet dot (no glow/trail)
        pygame.draw.circle(self.screen, self.colors['energy'], (int(x), int(y)), radius)

    def draw_hud(self, ammo_count, max_ammo, reloading, reload_start_time, last_fire_time, game_over):
        """Vẽ HUD"""
        hud_w, hud_h = 360, 140
        hud_x, hud_y = 20, 20

        # Background
        hud_bg = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
        hud_bg.fill((*self.colors['hud_bg'][:3], 200))
        self.screen.blit(hud_bg, (hud_x, hud_y))
        
        # Border
        pygame.draw.rect(self.screen, self.colors['accent'], 
                        (hud_x, hud_y, hud_w, hud_h), 2, border_radius=12)
        
        base_x, base_y = hud_x + 20, hud_y + 20

        # Ammo
        ammo_text = self.small_font.render("AMMO", True, self.colors['hud_text'])
        self.screen.blit(ammo_text, (base_x, base_y - 18))
        
        # Bullet indicators
        bullet_r, bullet_gap = 6, 4
        for i in range(max_ammo):
            bx = base_x + i * (bullet_r * 2 + bullet_gap)
            by = base_y
            center = (bx + bullet_r, by + bullet_r)
            
            if i < ammo_count:
                pygame.draw.circle(self.screen, self.colors['accent'], center, bullet_r)
                pygame.draw.circle(self.screen, self.colors['energy'], center, bullet_r-2)
            else:
                pygame.draw.circle(self.screen, self.colors['muted'], center, bullet_r)
                pygame.draw.circle(self.screen, self.colors['card_border'], center, bullet_r-2)
        
        # Ammo count
        ammo_count_text = self.font.render(f"{ammo_count}/{max_ammo}", True, self.colors['accent'])
        self.screen.blit(ammo_count_text, (base_x + 220, base_y))

        # Fire cooldown
        fire_cooldown = min(1.0, max(0.0, (time.time() - last_fire_time) / GameConstants.FIRE_COOLDOWN))
        self._draw_cooldown_bar(base_x, base_y + 35, 200, 12, fire_cooldown, "FIRE READY", "FIRING")

        # Reload
        if reloading:
            reload_progress = min(1.0, max(0.0, (time.time() - reload_start_time) / GameConstants.RELOAD_DURATION))
            self._draw_cooldown_bar(base_x, base_y + 55, 200, 12, reload_progress, "READY", "RELOADING")
        else:
            status = "PRESS R TO RELOAD" if ammo_count == 0 and not game_over else "READY"
            color = self.colors['yellow'] if ammo_count == 0 else self.colors['green']
            status_text = self.small_font.render(status, True, color)
            self.screen.blit(status_text, (base_x + 210, base_y + 55))

        # Map info
        map_text = self.font.render(f"MAP {self.current_map_id + 1}", True, self.colors['accent'])
        self.screen.blit(map_text, (self.original_width - 150, hud_y + 20))

    def _draw_cooldown_bar(self, x, y, width, height, progress, ready_text, cooldown_text):
        """Vẽ thanh cooldown"""
        # Background
        pygame.draw.rect(self.screen, self.colors['card_border'], (x, y, width, height), border_radius=6)
        
        # Fill
        if progress > 0:
            fill_w = int(width * progress)
            
            # Gradient
            for i in range(fill_w):
                ratio = i / fill_w
                r = int(self.colors['accent'][0] * ratio + self.colors['energy'][0] * (1-ratio))
                g = int(self.colors['accent'][1] * ratio + self.colors['energy'][1] * (1-ratio))
                b = int(self.colors['accent'][2] * ratio + self.colors['energy'][2] * (1-ratio))
                pygame.draw.rect(self.screen, (r, g, b), (x + i, y, 1, height))
        
        # Border
        pygame.draw.rect(self.screen, self.colors['accent'], (x, y, width, height), 1, border_radius=6)
        
        # Text
        text = ready_text if progress >= 1.0 else cooldown_text
        color = self.colors['green'] if progress >= 1.0 else self.colors['muted']
        text_surf = self.small_font.render(text, True, color)
        self.screen.blit(text_surf, (x + width + 10, y))

    def draw_game_over(self, winner_id, winner_name, waiting_for_restart):
        """Vẽ màn hình kết thúc game"""
        center_x, center_y = self._get_center()

        # Overlay
        overlay = pygame.Surface((self.original_width, self.original_height), pygame.SRCALPHA)
        for i in range(self.original_height):
            alpha = int(200 * (i / self.original_height))
            pygame.draw.line(overlay, (0, 0, 0, alpha), (0, i), (self.original_width, i))
        self.screen.blit(overlay, (0, 0))

        box_w, box_h = 700, 350
        left, top = center_x - box_w//2, center_y - box_h//2

        # Main card
        self._draw_glowing_card((left-10, top-10, box_w+20, box_h+20), self.colors['accent'], 15, 20)
        self._draw_card((left, top, box_w, box_h), 
                      color=self.colors['card'], 
                      border_color=self.colors['accent'],
                      radius=20)

        # Result
        if winner_id is None:
            result_text = "DRAW GAME"
            result_color = self.colors['muted']
            details_text = "No victors today"
        else:
            if str(winner_id) == str(self.player_id):
                result_text = "VICTORY ACHIEVED"
                result_color = self.colors['player']
                details_text = "You are the champion!"
            else:
                result_text = "MISSION FAILED"
                result_color = self.colors['enemy']
                details_text = f"{winner_name} was victorious"

        # Title
        title_surf = self.big_font.render("BATTLE REPORT", True, self.colors['accent'])
        self.screen.blit(title_surf, title_surf.get_rect(center=(center_x, top + 60)))

        # Result
        result_surf = self.big_font.render(result_text, True, result_color)
        self.screen.blit(result_surf, result_surf.get_rect(center=(center_x, top + 130)))

        # Details
        details_surf = self.font.render(details_text, True, self.colors['hud_text'])
        self.screen.blit(details_surf, details_surf.get_rect(center=(center_x, top + 180)))

        # Instructions
        if waiting_for_restart:
            restart_text = "AWAITING ORDERS..."
            restart_color = self.colors['muted']
        else:
            restart_text = "PRESS [T] TO DEPLOY AGAIN"
            restart_color = self.colors['accent']

        restart_surf = self.font.render(restart_text, True, restart_color)
        self.screen.blit(restart_surf, restart_surf.get_rect(center=(center_x, top + 230)))

        # Stats hint
        stats_text = self.small_font.render("COMBAT STATISTICS AVAILABLE IN BARRACKS", True, self.colors['muted'])
        self.screen.blit(stats_text, stats_text.get_rect(center=(center_x, top + 280)))

    def update_display(self):
        """Cập nhật màn hình"""
        pygame.display.flip()

    def cleanup(self):
        """Dọn dẹp tài nguyên"""
        pygame.quit()