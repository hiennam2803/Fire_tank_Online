import pygame
import math
import time
import random
import os
from common.messages import GameConstants

# Optional UI helper: pygame_gui (if installed)
try:
    import pygame_gui
    HAVE_PYGAME_GUI = True
except Exception:
    pygame_gui = None
    HAVE_PYGAME_GUI = False

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
        # Use a common Windows font to reduce glyph issues (falls back if not available)
        preferred_font = "Segoe UI"
        self.font = pygame.font.SysFont(preferred_font, 36)
        # Small font for placeholders and helper text
        self.small_font = pygame.font.SysFont(preferred_font, 18)
        self.big_font = pygame.font.SysFont(preferred_font, 72)

        # Tải các ảnh nền (background)
        self.load_backgrounds()
        # Đặt map mặc định ban đầu
        self.set_map(0)  # Map 0 làm mặc định
        # Tải logo nếu có
        try:
            logo_path = os.path.join('ui', 'logo.png')
            if os.path.exists(logo_path):
                self.logo = pygame.image.load(logo_path).convert_alpha()
            else:
                self.logo = None
        except Exception:
            self.logo = None

    def show_auth_menu(self):
        """Hiển thị màn hình chọn Login hoặc Register. Trả về 'login' hoặc 'register'"""
        if HAVE_PYGAME_GUI and self.screen is not None:
            # Simple pygame_gui menu
            manager = pygame_gui.UIManager(self.current_size)
            clock = pygame.time.Clock()
            cx, cy = self._get_center()
            w = 400; h = 120
            left = cx - w//2
            top = cy - h//2

            # draw rounded backgrounds for the buttons so they look more modern
            login_btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((left + 20, top + 20), (160, 80)), text='Login', manager=manager)
            reg_btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((left + 220, top + 20), (160, 80)), text='Register', manager=manager)

            running = True
            choice = 'login'
            while running:
                time_delta = clock.tick(60)/1000.0
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return None
                    if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == login_btn:
                            choice = 'login'
                            running = False
                        elif event.ui_element == reg_btn:
                            choice = 'register'
                            running = False
                    manager.process_events(event)
                manager.update(time_delta)
                # background + card
                self._draw_gradient_bg((18,20,30), (6,8,18))
                self._draw_card((left, top, w, h), color=(18,18,28), border_color=(60,60,70))
                # draw logo if available
                if getattr(self, 'logo', None):
                    logo = pygame.transform.smoothscale(self.logo, (96, 96))
                    # move logo higher so title and buttons have breathing room
                    self.screen.blit(logo, logo.get_rect(center=(cx, top - 120)))
                # Draw title above the buttons with a larger gap
                title = self.big_font.render('Welcome', True, (255,220,0))
                self.screen.blit(title, title.get_rect(center=(cx, top - 40)))
                # draw rounded rects behind GUI buttons to make them visually rounded
                pygame.draw.rect(self.screen, (70,70,70), pygame.Rect(left + 20, top + 20, 160, 80), border_radius=12)
                pygame.draw.rect(self.screen, (70,70,70), pygame.Rect(left + 220, top + 20, 160, 80), border_radius=12)
                manager.draw_ui(self.screen)
                pygame.display.update()
            return choice
        # Fallback custom menu
        clock = pygame.time.Clock()
        cx, cy = self._get_center()
        w = 500; h = 180
        left = cx - w//2
        top = cy - h//2
        running = True
        choice = 'login'
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx,my = event.pos
                    login_rect = pygame.Rect(left + 40, top + 40, 180, 80)
                    reg_rect = pygame.Rect(left + 280, top + 40, 180, 80)
                    if login_rect.collidepoint(mx,my):
                        choice='login'; running=False
                    if reg_rect.collidepoint(mx,my):
                        choice='register'; running=False

            self.screen.fill((10,10,20))
            # Styled background + card
            self._draw_gradient_bg((18,20,30), (6,8,18))
            self._draw_card((left, top, w, h), color=(18,18,28), border_color=(60,60,70))
            # draw logo if available
            if getattr(self, 'logo', None):
                logo = pygame.transform.smoothscale(self.logo, (96,96))
                self.screen.blit(logo, logo.get_rect(center=(cx, top - 120)))
            # Title above buttons with larger spacing
            title = self.big_font.render('Welcome', True, (255,220,0))
            self.screen.blit(title, title.get_rect(center=(cx, top - 40)))
            # Buttons (rounded)
            login_rect = pygame.Rect(left + 40, top + 40, 180, 80)
            reg_rect = pygame.Rect(left + 280, top + 40, 180, 80)
            pygame.draw.rect(self.screen, (80,80,80), login_rect, border_radius=12)
            pygame.draw.rect(self.screen, (80,80,80), reg_rect, border_radius=12)
            ltxt = self.font.render('Login', True, (220,220,220))
            rtxt = self.font.render('Register', True, (220,220,220))
            self.screen.blit(ltxt, ltxt.get_rect(center=login_rect.center))
            self.screen.blit(rtxt, rtxt.get_rect(center=reg_rect.center))
            pygame.display.flip()
            clock.tick(30)
        return choice

    def _draw_input_box(self, rect, text, active=False, password=False):
        """Vẽ hộp nhập liệu đơn giản và trả về rect để xử lý sự kiện"""
        color = (255, 255, 255) if active else (180, 180, 180)
        pygame.draw.rect(self.screen, (20, 20, 20), rect)
        pygame.draw.rect(self.screen, color, rect, 2)
        display_text = text
        if password:
            display_text = '*' * len(text)
        # Nếu rỗng và không active, hiển thị placeholder mờ
        if not display_text:
            # placeholder will be rendered by caller when needed
            txt_surf = self.font.render('', True, (230, 230, 230))
        else:
            txt_surf = self.font.render(display_text, True, (230, 230, 230))
        txt_rect = txt_surf.get_rect(midleft=(rect.x + 8, rect.centery))
        self.screen.blit(txt_surf, txt_rect)

    def _draw_gradient_bg(self, top_color=(20,24,40), bottom_color=(6,8,18)):
        """Vẽ background gradient dọc từ top_color xuống bottom_color."""
        w, h = self.current_size
        grad = pygame.Surface((1, h)).convert_alpha()
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
            g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
            b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
            grad.set_at((0, y), (r, g, b))
        grad = pygame.transform.scale(grad, (w, h))
        self.screen.blit(grad, (0, 0))

    def _draw_card(self, rect, color=(18,18,28), radius=10, border_color=None):
        """Vẽ thẻ (card) nền để chứa form với bo góc."""
        s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.rect(s, color, (0, 0, rect[2], rect[3]), border_radius=radius)
        if border_color:
            pygame.draw.rect(s, border_color, (0, 0, rect[2], rect[3]), 2, border_radius=radius)
        self.screen.blit(s, (rect[0], rect[1]))

    def show_login_screen(self):
        """Hiển thị màn hình đăng nhập / đăng ký. Nếu `pygame_gui` có sẵn sẽ dùng widget đẹp hơn.
        Trả về dict với host, type, username, password, name
        """
        # Nếu có màn hình, hiển thị menu lựa chọn trước (Login / Register)
        selection = None
        if self.screen is not None:
            try:
                selection = self.show_auth_menu()
            except Exception:
                selection = None

        # Loop: show menu, then page; allow pages to return {'action':'back'} to re-open menu
        while True:
            selection = None
            if self.screen is not None:
                try:
                    selection = self.show_auth_menu()
                except Exception:
                    selection = None

            # If user closed the menu
            if selection is None:
                return None

            # Choose GUI variant
            if HAVE_PYGAME_GUI and self.screen is not None:
                try:
                    if selection == 'register':
                        res = self._show_register_with_pygame_gui()
                    else:
                        res = self._show_login_with_pygame_gui()
                except Exception:
                    print("Warning: pygame_gui login failed, falling back to builtin login UI")
                    res = None
            else:
                if selection == 'register':
                    res = self._show_register_page_custom()
                else:
                    res = self._show_login_page_custom()

            # None = closed; {'action':'back'} = go back to selection; otherwise return result
            if res is None:
                return None
            if isinstance(res, dict) and res.get('action') == 'back':
                continue
            return res

    def _show_login_with_pygame_gui(self):
        """Hiển thị màn hình đăng nhập bằng pygame_gui. Trả về dict giống show_login_screen."""
        if not HAVE_PYGAME_GUI:
            raise RuntimeError("pygame_gui not available")

        manager = pygame_gui.UIManager(self.current_size)
        clock = pygame.time.Clock()

        cx, cy = self._get_center()
        box_w = min(600, self.current_size[0] - 100)
        box_h = 260
        left = cx - box_w // 2
        top = cy - box_h // 2

        # Title label (we'll draw it manually for nicer font)
        title_surf = self.big_font.render("Fire Tank", True, (255, 220, 0))

        # Input fields
        host_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((left + 20, top + 60), (box_w - 40, 36)),
            manager=manager,
            object_id="#host"
        )
        username_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((left + 20, top + 100), (box_w - 40, 36)),
            manager=manager,
            object_id="#username"
        )
        password_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((left + 20, top + 140), (box_w - 40, 36)),
            manager=manager,
            object_id="#password"
        )
        password_input.set_text_hidden(True)

        login_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((left + 20, top + 190), ((box_w - 60) // 2, 40)),
            text='Login',
            manager=manager
        )
        # Use a single Login button on the login page (Register is on the separate page)
        login_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((left + 20, top + 190), (box_w - 40, 40)),
            text='Login',
            manager=manager
        )
        back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((left + 20, top + 20), (80, 30)),
            text='Back',
            manager=manager
        )

        # Placeholders
        host_input.set_text('')
        username_input.set_text('')
        password_input.set_text('')

        # Helper text
        info_label = None

        running = True
        result = None
        while running:
            time_delta = clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.USEREVENT:
                    if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == back_button:
                            return {'action': 'back'}
                        if event.ui_element == login_button:
                            result = {
                                'host': (host_input.get_text() or 'localhost').strip(),
                                'type': 'login',
                                'username': username_input.get_text().strip(),
                                'password': password_input.get_text(),
                                'name': None
                            }
                            running = False

                manager.process_events(event)

            manager.update(time_delta)

            # Draw background card
            # Styled background
            self._draw_gradient_bg((24, 28, 48), (6, 8, 18))
            # Card
            self._draw_card((left, top, box_w, box_h), color=(22, 22, 30), border_color=(70,70,80))
            # Title with shadow
            shadow = self.big_font.render("Fire Tank", True, (10, 10, 10))
            self.screen.blit(shadow, shadow.get_rect(center=(cx + 2, top + 32)))
            self.screen.blit(title_surf, title_surf.get_rect(center=(cx, top + 30)))
            manager.draw_ui(self.screen)

            
            try:
                if host_input.get_text() == '':
                    ph = self.small_font.render('Ví dụ: 127.0.0.1 hoặc 192.168.1.2', True, (160, 160, 170))
                    self.screen.blit(ph, (left + 26, top + 60 + (36 - ph.get_height()) // 2))
                if username_input.get_text() == '':
                    ph = self.small_font.render('Tên đăng nhập (ví dụ: player1)', True, (160, 160, 170))
                    self.screen.blit(ph, (left + 26, top + 100 + (36 - ph.get_height()) // 2))
                if password_input.get_text() == '':
                    ph = self.small_font.render('Mật khẩu', True, (160, 160, 170))
                    self.screen.blit(ph, (left + 26, top + 140 + (36 - ph.get_height()) // 2))
            except Exception:
                
                pass
            pygame.display.update()

        return result
    
    def _show_login_page_custom(self):
        """Custom pygame login page (host + username + password)."""
        host = ''
        username = ''
        password = ''

        active = 0  # 0:host,1:username,2:password
        clock = pygame.time.Clock()
        running = True
        while running:
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
                        if active == 0 and host:
                            host = host[:-1]
                        elif active == 1 and username:
                            username = username[:-1]
                        elif active == 2 and password:
                            password = password[:-1]
                    else:
                        ch = event.unicode
                        if ch:
                            if active == 0:
                                host += ch
                            elif active == 1:
                                username += ch
                            elif active == 2:
                                password += ch

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    hw = 400; hh = 40
                    cx, cy = self._get_center()
                    start_x = cx - hw//2
                    y0 = 160
                    boxes = [pygame.Rect(start_x, y0, hw, hh),
                             pygame.Rect(start_x, y0 + 60, hw, hh),
                             pygame.Rect(start_x, y0 + 120, hw, hh)]
                    for i, r in enumerate(boxes):
                        if r.collidepoint(mx, my):
                            active = i
                    # Back button area
                    back_rect = pygame.Rect(start_x - 100, y0 - 48, 80, 30)
                    if back_rect.collidepoint(mx, my):
                        return {'action': 'back'}

            # Draw
            # Gradient background + card
            self._draw_gradient_bg((24, 28, 48), (6, 8, 18))
            title = self.big_font.render("Fire Tank - Login", True, (255, 220, 0))
            tx, ty = self._get_center()
            # card
            hw = 400; hh = 40
            start_x = tx - hw//2
            y0 = 160
            card_h = 320
            self._draw_card((start_x - 40, y0 - 80, hw + 80, card_h), color=(22,22,30), border_color=(60,60,70))
            # title with shadow
            shadow = self.big_font.render("Fire Tank - Login", True, (10,10,10))
            self.screen.blit(shadow, shadow.get_rect(center=(tx + 2, 82)))
            self.screen.blit(title, title.get_rect(center=(tx, 80)))

            hw = 400; hh = 40
            start_x = tx - hw//2
            y0 = 160

            host_rect = pygame.Rect(start_x, y0, hw, hh)
            self._draw_input_box(host_rect, host, active == 0, password=False)
            host_label = self.font.render("Server IP (hoac IP, de trong = localhost)", True, (200,200,200))
            self.screen.blit(host_label, (start_x, y0 - 28))
            if not host and active != 0:
                ph = self.small_font.render("Vi du: localhost hoặc 192.168.1.2", True, (120,120,120))
                ph_pos = (host_rect.x + 8, host_rect.y + (host_rect.height - ph.get_height()) // 2)
                self.screen.blit(ph, ph_pos)

            user_rect = pygame.Rect(start_x, y0 + 60, hw, hh)
            self._draw_input_box(user_rect, username, active == 1)
            user_label = self.font.render("Ten tai khoan", True, (200,200,200))
            self.screen.blit(user_label, (start_x, y0 + 60 - 28))
            if not username and active != 1:
                ph = self.small_font.render("Ten dang nhap (vi du: player1)", True, (120,120,120))
                ph_pos = (user_rect.x + 8, user_rect.y + (user_rect.height - ph.get_height()) // 2)
                self.screen.blit(ph, ph_pos)

            pass_rect = pygame.Rect(start_x, y0 + 120, hw, hh)
            self._draw_input_box(pass_rect, password, active == 2, password=True)
            pass_label = self.font.render("Mat khau", True, (200,200,200))
            self.screen.blit(pass_label, (start_x, y0 + 120 - 28))
            if not password and active != 2:
                ph = self.small_font.render("Mat khau (an khi go)", True, (120,120,120))
                ph_pos = (pass_rect.x + 8, pass_rect.y + (pass_rect.height - ph.get_height()) // 2)
                self.screen.blit(ph, ph_pos)

            info = self.font.render("Enter to submit. Click fields to focus.", True, (220,220,220))
            self.screen.blit(info, info.get_rect(center=(tx, y0 + 220)))

            # Draw Back button
            back_rect = pygame.Rect(start_x - 100, y0 - 48, 80, 30)
            pygame.draw.rect(self.screen, (80,80,80), back_rect)
            btxt = self.small_font.render('Back', True, (230,230,230))
            self.screen.blit(btxt, btxt.get_rect(center=back_rect.center))

            pygame.display.flip()
            clock.tick(30)

        if not host or host.strip() == '':
            host = 'localhost'
        return {
            'host': host.strip(),
            'type': 'login',
            'username': username.strip(),
            'password': password,
            'name': None
        }

    def _show_register_page_custom(self):
        """Custom pygame register page (host + username + password + display name)."""
        host = ''
        username = ''
        password = ''
        name = ''

        active = 0  # 0:host,1:username,2:password,3:name
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return {'action': 'back'}
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_TAB:
                        active = (active + 1) % 4
                    elif event.key == pygame.K_RETURN:
                        if username and password and name:
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
                    hw = 400; hh = 40
                    cx, cy = self._get_center()
                    start_x = cx - hw//2
                    y0 = 160
                    boxes = [pygame.Rect(start_x, y0, hw, hh),
                             pygame.Rect(start_x, y0 + 60, hw, hh),
                             pygame.Rect(start_x, y0 + 120, hw, hh),
                             pygame.Rect(start_x, y0 + 180, hw, hh)]
                    for i, r in enumerate(boxes):
                        if r.collidepoint(mx, my):
                            active = i
                    # Back button
                    back_rect = pygame.Rect(start_x - 100, y0 - 48, 80, 30)
                    if back_rect.collidepoint(mx, my):
                        return {'action': 'back'}

            # Draw
            self.screen.fill((10, 10, 30))
            title = self.big_font.render("Fire Tank - Register", True, (255, 220, 0))
            tx, ty = self._get_center()
            self.screen.blit(title, title.get_rect(center=(tx, 80)))

            hw = 400; hh = 40
            start_x = tx - hw//2
            y0 = 160

            host_rect = pygame.Rect(start_x, y0, hw, hh)
            self._draw_input_box(host_rect, host, active == 0, password=False)
            host_label = self.font.render("Server IP (hoac IP, de trong = localhost)", True, (200,200,200))
            self.screen.blit(host_label, (start_x, y0 - 28))
            if not host and active != 0:
                ph = self.small_font.render("Vi du: localhost hoặc 192.168.1.2", True, (120,120,120))
                ph_pos = (host_rect.x + 8, host_rect.y + (host_rect.height - ph.get_height()) // 2)
                self.screen.blit(ph, ph_pos)

            user_rect = pygame.Rect(start_x, y0 + 60, hw, hh)
            self._draw_input_box(user_rect, username, active == 1)
            user_label = self.font.render("Ten tai khoan", True, (200,200,200))
            self.screen.blit(user_label, (start_x, y0 + 60 - 28))
            if not username and active != 1:
                ph = self.small_font.render("Ten dang nhap (vi du: player1)", True, (120,120,120))
                ph_pos = (user_rect.x + 8, user_rect.y + (user_rect.height - ph.get_height()) // 2)
                self.screen.blit(ph, ph_pos)

            pass_rect = pygame.Rect(start_x, y0 + 120, hw, hh)
            self._draw_input_box(pass_rect, password, active == 2, password=True)
            pass_label = self.font.render("Mat khau", True, (200,200,200))
            self.screen.blit(pass_label, (start_x, y0 + 120 - 28))
            if not password and active != 2:
                ph = self.small_font.render("Mat khau (an khi go)", True, (120,120,120))
                ph_pos = (pass_rect.x + 8, pass_rect.y + (pass_rect.height - ph.get_height()) // 2)
                self.screen.blit(ph, ph_pos)

            name_rect = pygame.Rect(start_x, y0 + 180, hw, hh)
            self._draw_input_box(name_rect, name, active == 3)
            name_label = self.font.render("Ten hien thi (dang ky)", True, (180,180,180))
            self.screen.blit(name_label, (start_x, y0 + 180 - 28))
            if not name and active != 3:
                ph = self.small_font.render("Ten hien thi se hien trong tran", True, (120,120,120))
                ph_pos = (name_rect.x + 8, name_rect.y + (name_rect.height - ph.get_height()) // 2)
                self.screen.blit(ph, ph_pos)

            # Draw styled buttons area (visual only)
            btn_w = 160; btn_h = 40
            login_btn_rect = pygame.Rect(tx - btn_w - 20, y0 + 220, btn_w, btn_h)
            pygame.draw.rect(self.screen, (70,70,80), login_btn_rect, border_radius=6)
            ltxt = self.font.render('Login', True, (230,230,230))
            self.screen.blit(ltxt, ltxt.get_rect(center=login_btn_rect.center))

            pygame.display.flip()
            back_rect = pygame.Rect(start_x - 100, y0 - 48, 80, 30)
            pygame.draw.rect(self.screen, (80,80,80), back_rect)
            btxt = self.small_font.render('Back', True, (230,230,230))
            self.screen.blit(btxt, btxt.get_rect(center=back_rect.center))

            pygame.display.flip()
            clock.tick(30)

        if not host or host.strip() == '':
            host = 'localhost'
        return {
            'host': host.strip(),
            'type': 'register',
            'username': username.strip(),
            'password': password,
            'name': name.strip() if name.strip() else None
        }

    def _show_register_with_pygame_gui(self):
        """Pygame_gui variant of register page (adds display name field)."""
        if not HAVE_PYGAME_GUI:
            raise RuntimeError("pygame_gui not available")

        manager = pygame_gui.UIManager(self.current_size)
        clock = pygame.time.Clock()

        cx, cy = self._get_center()
        box_w = min(600, self.current_size[0] - 100)
        box_h = 320
        left = cx - box_w // 2
        top = cy - box_h // 2

        title_surf = self.big_font.render("Fire Tank", True, (255, 220, 0))

        host_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((left + 20, top + 60), (box_w - 40, 36)),
            manager=manager,
            object_id="#host"
        )
        username_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((left + 20, top + 100), (box_w - 40, 36)),
            manager=manager,
            object_id="#username"
        )
        password_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((left + 20, top + 140), (box_w - 40, 36)),
            manager=manager,
            object_id="#password"
        )
        password_input.set_text_hidden(True)

        name_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((left + 20, top + 180), (box_w - 40, 36)),
            manager=manager,
            object_id="#name"
        )

        register_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((left + 20, top + 230), (box_w - 40, 40)),
            text='Register',
            manager=manager
        )
        back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((left + 20, top + 20), (80, 30)),
            text='Back',
            manager=manager
        )

        host_input.set_text('')
        username_input.set_text('')
        password_input.set_text('')
        name_input.set_text('')

        running = True
        result = None
        while running:
            time_delta = clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.USEREVENT:
                    if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == back_button:
                            return {'action': 'back'}
                        if event.ui_element == register_button:
                            result = {
                                'host': (host_input.get_text() or 'localhost').strip(),
                                'type': 'register',
                                'username': username_input.get_text().strip(),
                                'password': password_input.get_text(),
                                'name': name_input.get_text().strip() or None
                            }
                            running = False

                manager.process_events(event)

            manager.update(time_delta)

            # Styled background + card
            self._draw_gradient_bg((24, 28, 48), (6, 8, 18))
            self._draw_card((left, top, box_w, box_h), color=(22,22,30), border_color=(70,70,80))
            shadow = self.big_font.render("Fire Tank", True, (10, 10, 10))
            self.screen.blit(shadow, shadow.get_rect(center=(cx + 2, top + 32)))
            self.screen.blit(title_surf, title_surf.get_rect(center=(cx, top + 30)))
            manager.draw_ui(self.screen)

            try:
                if host_input.get_text() == '':
                    ph = self.small_font.render('Ví dụ: 127.0.0.1 hoặc 192.168.1.2', True, (160,160,170))
                    self.screen.blit(ph, (left + 26, top + 60 + (36 - ph.get_height()) // 2))
                if username_input.get_text() == '':
                    ph = self.small_font.render('Tên đăng nhập (ví dụ: player1)', True, (160,160,170))
                    self.screen.blit(ph, (left + 26, top + 100 + (36 - ph.get_height()) // 2))
                if password_input.get_text() == '':
                    ph = self.small_font.render('Mật khẩu', True, (160,160,170))
                    self.screen.blit(ph, (left + 26, top + 140 + (36 - ph.get_height()) // 2))
                if name_input.get_text() == '':
                    ph = self.small_font.render('Tên hiển thị (ví dụ: Player One)', True, (160,160,170))
                    self.screen.blit(ph, (left + 26, top + 180 + (36 - ph.get_height()) // 2))
            except Exception:
                pass

            pygame.display.update()

        return result
    
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
        # Simplified, clearer layout:
        # Title top, player id under title, status centered, map thumbnail left, players row under map,
        # progress bar centered under players, controls block on right.
        self.draw_background()
        overlay = pygame.Surface(self.current_size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        cx, cy = self._get_center()

        # Title
        title_text = self.big_font.render("TANK BATTLE", True, (250, 220, 20))
        title_rect = title_text.get_rect(center=(cx, int(self._scale_value(100, False))))
        self.screen.blit(title_text, title_rect)

        # Player ID just below title
        id_surf = self.font.render(f"Player ID: {self.player_id}", True, (64, 220, 220))
        self.screen.blit(id_surf, id_surf.get_rect(center=(cx, int(self._scale_value(150, False)))))

        # Status (centered under player id)
        t = time.time()
        dots = int((t * 2) % 4)
        dot_str = "." * dots
        if waiting_for_players:
            status_str = f"Waiting for more players to join{dot_str}"
            status_color = (255, 200, 40)
        elif ready:
            status_str = "READY - Waiting for other players..."
            status_color = (80, 220, 120)
        else:
            status_str = "Press SPACE to ready up"
            status_color = (220, 200, 80)
        status_surf = self.font.render(status_str, True, status_color)
        self.screen.blit(status_surf, status_surf.get_rect(center=(cx, int(self._scale_value(200, False)))))

        # Map thumbnail on the left
        thumb_w = int(self._scale_value(260))
        thumb_h = int(self._scale_value(140, False))
        thumb_x = cx - int(self._scale_value(320))
        thumb_y = int(self._scale_value(240, False))
        if self.current_background:
            try:
                thumb = pygame.transform.smoothscale(self.current_background, (thumb_w, thumb_h))
                self._draw_card((thumb_x - 10, thumb_y - 10, thumb_w + 20, thumb_h + 20), color=(18,18,22), border_color=(60,60,70))
                self.screen.blit(thumb, (thumb_x, thumb_y))
                map_label = self.small_font.render(f"Map {self.current_map_id + 1}", True, (220, 200, 120))
                self.screen.blit(map_label, (thumb_x + thumb_w//2 - map_label.get_width()//2, thumb_y + thumb_h + 8))
            except Exception:
                pass

        # Players icons row under thumbnail
        players = []
        if game_state and isinstance(game_state, dict) and 'players' in game_state:
            for pid, pdata in game_state['players'].items():
                display = pdata.get('name') if isinstance(pdata, dict) and pdata.get('name') else f"Player {pid}"
                is_ready = bool(pdata.get('ready')) if isinstance(pdata, dict) else False
                players.append((str(pid), display, is_ready))

        icon_size = int(self._scale_value(50))
        gap = int(self._scale_value(20))
        total_width = len(players) * icon_size + max(0, len(players)-1) * gap
        start_x = thumb_x + (thumb_w - total_width) // 2 if total_width > 0 else thumb_x
        py = thumb_y + thumb_h + int(self._scale_value(50, False))
        for i, (pid, name, is_ready) in enumerate(players):
            x = start_x + i * (icon_size + gap)
            bg_color = (40, 60, 90) if str(pid) != str(self.player_id) else (20, 120, 80)
            pygame.draw.circle(self.screen, bg_color, (x + icon_size//2, py), icon_size//2)
            letter = (name[0].upper() if name else '?')
            letter_s = self.small_font.render(letter, True, (240,240,240))
            self.screen.blit(letter_s, letter_s.get_rect(center=(x + icon_size//2, py)))
            tick_color = (80, 220, 120) if is_ready else (160,160,160)
            pygame.draw.circle(self.screen, tick_color, (x + icon_size - 10, py + icon_size//2 - 10), 8)
            name_s = self.small_font.render(name, True, (220,220,230))
            self.screen.blit(name_s, (x + (icon_size - name_s.get_width())//2, py + icon_size//2 + 12))

        # Progress bar centered under players
        total_needed = GameConstants.MAX_PLAYERS
        connected = max(0, len(players))
        bar_w = int(self._scale_value(420))
        bar_h = int(self._scale_value(18, False))
        bar_x = cx - bar_w // 2
        bar_y = py + int(self._scale_value(60, False))
        pygame.draw.rect(self.screen, (60,60,70), (bar_x, bar_y, bar_w, bar_h), border_radius=10)
        if total_needed > 0:
            fill_w = int(bar_w * (connected / total_needed))
            pygame.draw.rect(self.screen, (40,200,120), (bar_x, bar_y, fill_w, bar_h), border_radius=10)
        pct_s = self.small_font.render(f"{connected}/{total_needed} connected", True, (220,220,230))
        self.screen.blit(pct_s, pct_s.get_rect(center=(cx, bar_y + bar_h//2)))

        # Controls block on the right, aligned vertically
        instr_x = cx + int(self._scale_value(260))
        instr_y = int(self._scale_value(220, False))
        heading = self.font.render("CONTROLS", True, (200,200,200))
        self.screen.blit(heading, heading.get_rect(center=(instr_x, instr_y)))
        controls = [
            "ARROW KEYS - Move tank & aim",
            "SPACE - Fire",
            "R - Reload",
            "T - Restart (after game over)",
            "F - Toggle fullscreen"
        ]
        for i, c in enumerate(controls):
            txt = self.small_font.render(c, True, (200,200,200))
            self.screen.blit(txt, (instr_x - self._scale_value(110), instr_y + 30 + i * self._scale_value(28, False)))

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
                base_color = (0, 255, 0)  # Xanh lá - player hiện tại
                dark_color = (0, 150, 0)  # Xanh đậm cho chi tiết
            else:
                base_color = (255, 0, 0)  # Đỏ - đối thủ
                dark_color = (150, 0, 0)  # Đỏ đậm cho chi tiết
            
            # Tính toán vị trí
            x, y = self._scale_position(player['x'], player['y'])
            tank_size = self._scale_value(40)
            tank_width = tank_size
            tank_height = tank_size * 0.6
            
            # Vẽ thân xe (hình chữ nhật bo góc)
            body_rect = pygame.Rect(
                int(x - tank_width/2),
                int(y - tank_height/2),
                int(tank_width),
                int(tank_height)
            )
            pygame.draw.rect(self.screen, base_color, body_rect, border_radius=int(tank_size*0.1))
            
            # Vẽ viền thân xe
            pygame.draw.rect(self.screen, dark_color, body_rect, 2, border_radius=int(tank_size*0.1))
            
            # Vẽ bánh xe
            wheel_width = tank_width * 0.1
            wheel_height = tank_height * 0.3
            
            # Bánh trước
            front_wheel_rect = pygame.Rect(
                int(x + tank_width/2 - wheel_width),
                int(y - wheel_height/2),
                int(wheel_width),
                int(wheel_height)
            )
            pygame.draw.rect(self.screen, dark_color, front_wheel_rect, border_radius=int(wheel_width*0.3))
            
            # Bánh sau
            back_wheel_rect = pygame.Rect(
                int(x - tank_width/2),
                int(y - wheel_height/2),
                int(wheel_width),
                int(wheel_height)
            )
            pygame.draw.rect(self.screen, dark_color, back_wheel_rect, border_radius=int(wheel_width*0.3))
            
            # Bánh giữa (nếu tank đủ lớn)
            if tank_width > 30:
                center_wheel_rect = pygame.Rect(
                    int(x - wheel_width/2),
                    int(y - wheel_height/2),
                    int(wheel_width),
                    int(wheel_height)
                )
                pygame.draw.rect(self.screen, dark_color, center_wheel_rect, border_radius=int(wheel_width*0.3))
            
            # Vẽ tháp pháo (hình tròn)
            turret_radius = tank_size * 0.25
            pygame.draw.circle(self.screen, base_color, (int(x), int(y)), int(turret_radius))
            pygame.draw.circle(self.screen, dark_color, (int(x), int(y)), int(turret_radius), 2)
            
            # Vẽ nòng súng
            barrel_length = tank_size * 0.8
            end_x = x + barrel_length * math.cos(math.radians(player['angle']))
            end_y = y + barrel_length * math.sin(math.radians(player['angle']))
            
            # Vẽ nòng súng (hình chữ nhật dày hơn)
            barrel_width = tank_size * 0.08
            barrel_vector = pygame.Vector2(barrel_length * math.cos(math.radians(player['angle'])), 
                                        barrel_length * math.sin(math.radians(player['angle'])))
            perpendicular = pygame.Vector2(-barrel_vector.y, barrel_vector.x).normalize() * (barrel_width/2)
            
            barrel_points = [
                (x + perpendicular.x, y + perpendicular.y),
                (x - perpendicular.x, y - perpendicular.y),
                (end_x - perpendicular.x, end_y - perpendicular.y),
                (end_x + perpendicular.x, end_y + perpendicular.y)
            ]
            
            pygame.draw.polygon(self.screen, dark_color, barrel_points)
            
            # Vẽ thanh HP (giữ nguyên logic cũ nhưng đẹp hơn)
            bar_width = self._scale_value(50)
            bar_height = self._scale_value(5)
            bar_x = x - self._scale_value(25)
            bar_y = y - self._scale_value(40)
            
            # Nền thanh máu
            pygame.draw.rect(self.screen, (255, 0, 0), (bar_x, bar_y, bar_width, bar_height))
            
            # Máu hiện tại
            hp_width = self._scale_value(player['hp']/2)
            pygame.draw.rect(self.screen, (0, 255, 0), (bar_x, bar_y, hp_width, bar_height))
    # Vẽ viên đạn
        for bullet in game_state['bullets']:
            x, y = self._scale_position(bullet['x'], bullet['y'])
            radius = self._scale_value(5)
            
            # Vẽ hiệu ứng khói/lửa phía sau đạn
            trail_length = self._scale_value(15)
            start_x = x - trail_length * math.cos(math.radians(bullet['angle']))
            start_y = y - trail_length * math.sin(math.radians(bullet['angle']))
            
            # Vẽ vệt lửa với gradient màu
            for i in range(3):
                trail_factor = 0.3 + i * 0.2  # Tạo 3 lớp vệt với độ dài khác nhau
                trail_start_x = x - trail_length * trail_factor * math.cos(math.radians(bullet['angle']))
                trail_start_y = y - trail_length * trail_factor * math.sin(math.radians(bullet['angle']))
                
                # Màu sắc từ vàng (gần đạn) đến cam/đỏ (xa đạn)
                if i == 0:
                    trail_color = (255, 200, 0)  # Vàng cam
                    trail_width = int(self._scale_value(3))
                elif i == 1:
                    trail_color = (255, 100, 0)  # Cam
                    trail_width = int(self._scale_value(2))
                else:
                    trail_color = (200, 50, 0)   # Cam đỏ
                    trail_width = int(self._scale_value(1))
                    
                pygame.draw.line(self.screen, trail_color, 
                                (trail_start_x, trail_start_y), 
                                (x, y), trail_width)
            
            # Vẽ viên đạn chính với hiệu ứng lửa
            # Lõi đạn màu trắng sáng
            pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), int(radius))
            
            # Lớp giữa màu vàng cam
            middle_radius = radius * 0.7
            pygame.draw.circle(self.screen, (255, 200, 0), (int(x), int(y)), int(middle_radius))
            
            # Lớp ngoài cùng màu cam đỏ
            outer_radius = radius * 0.4
            pygame.draw.circle(self.screen, (255, 100, 0), (int(x), int(y)), int(outer_radius))
            
            # Hiệu ứng tia lửa xung quanh
            spark_count = 6
            spark_length = self._scale_value(4)
            for i in range(spark_count):
                angle_offset = i * (360 / spark_count)
                spark_angle = bullet['angle'] + angle_offset
                spark_end_x = x + spark_length * math.cos(math.radians(spark_angle))
                spark_end_y = y + spark_length * math.sin(math.radians(spark_angle))
                
                pygame.draw.line(self.screen, (255, 255, 100), 
                                (int(x), int(y)), 
                                (int(spark_end_x), int(spark_end_y)), 
                                int(self._scale_value(1)))

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