import pygame
import math
import time
from common.messages import GameConstants

class GameRenderer:
    def __init__(self, player_id):
        self.player_id = player_id
        self.screen = None
        self.font = None
        self.big_font = None
        
    def initialize(self):
        """Khởi tạo pygame và fonts"""
        pygame.init()
        self.screen = pygame.display.set_mode((GameConstants.SCREEN_WIDTH, GameConstants.SCREEN_HEIGHT))
        pygame.display.set_caption(f"Tank Battle - Player {self.player_id}")
        self.font = pygame.font.SysFont(None, 36)
        self.big_font = pygame.font.SysFont(None, 72)
    
    def draw_waiting_screen(self, game_state, ready, waiting_for_players):
        """Vẽ màn hình chờ"""
        self.screen.fill((0, 0, 50))  # Dark blue background
        
        # Title
        title_text = self.big_font.render("TANK BATTLE", True, (255, 255, 0))
        title_rect = title_text.get_rect(center=(400, 150))
        self.screen.blit(title_text, title_rect)
        
        # Player ID
        id_text = self.font.render(f"Player ID: {self.player_id}", True, (0, 255, 255))
        id_rect = id_text.get_rect(center=(400, 220))
        self.screen.blit(id_text, id_rect)
        
        # Status message
        if waiting_for_players:
            status_text = self.font.render("Waiting for more players to join...", True, (255, 255, 0))
        elif ready:
            status_text = self.font.render("READY - Waiting for other players...", True, (0, 255, 0))
        else:
            status_text = self.font.render("Press SPACE to ready up", True, (255, 200, 0))
        
        status_rect = status_text.get_rect(center=(400, 270))
        self.screen.blit(status_text, status_rect)
        
        # Player count info
        if game_state and 'players' in game_state:
            player_count = len(game_state['players'])
            count_text = self.font.render(f"Players connected: {player_count}/2", True, (200, 200, 255))
            count_rect = count_text.get_rect(center=(400, 320))
            self.screen.blit(count_text, count_rect)
        
        # Instructions
        instructions = [
            "CONTROLS:",
            "ARROW KEYS - Move tank and aim",
            "SPACE - Fire weapon",
            "R - Reload ammo",
            "T - Restart (after game over)"
        ]
        
        for i, line in enumerate(instructions):
            text = self.font.render(line, True, (200, 200, 200))
            self.screen.blit(text, (250, 370 + i * 40))

    def draw_game_state(self, game_state):
        """Vẽ game state (players, bullets, etc.)"""
        if not game_state:
            return
            
        # Draw players
        for pid, player in game_state['players'].items():
            color = (0, 255, 0) if pid == self.player_id else (255, 0, 0)
            pygame.draw.circle(self.screen, color, (int(player['x']), int(player['y'])), 20)
            
            # Draw tank turret
            end_x = player['x'] + 25 * math.cos(math.radians(player['angle']))
            end_y = player['y'] + 25 * math.sin(math.radians(player['angle']))
            pygame.draw.line(self.screen, color, (player['x'], player['y']), (end_x, end_y), 5)
            
            # Draw HP bar
            pygame.draw.rect(self.screen, (255,0,0), (player['x']-25, player['y']-40, 50, 5))
            pygame.draw.rect(self.screen, (0,255,0), (player['x']-25, player['y']-40, player['hp']/2, 5))

        # Draw bullets
        for bullet in game_state['bullets']:
            pygame.draw.circle(self.screen, (255, 255, 0), (int(bullet['x']), int(bullet['y'])), 5)
            
            # Draw bullet trail
            trail_length = 10
            start_x = bullet['x'] - trail_length * math.cos(math.radians(bullet['angle']))
            start_y = bullet['y'] - trail_length * math.sin(math.radians(bullet['angle']))
            pygame.draw.line(self.screen, (255, 200, 0), 
                            (start_x, start_y), 
                            (bullet['x'], bullet['y']), 2)

    def draw_hud(self, ammo_count, max_ammo, reloading, reload_start_time, last_fire_time, game_over):
        """Vẽ HUD với thông tin game"""
        # Draw ammo counter
        ammo_color = (255, 255, 255)
        if ammo_count == 0:
            ammo_color = (255, 0, 0)
        elif ammo_count <= 3:
            ammo_color = (255, 165, 0)
            
        ammo_text = self.font.render(f"Ammo: {ammo_count}/{max_ammo}", True, ammo_color)
        self.screen.blit(ammo_text, (10, 10))
        
        # Draw fire cooldown indicator
        fire_cooldown_percent = min(1.0, (time.time() - last_fire_time) / GameConstants.FIRE_COOLDOWN)
        pygame.draw.rect(self.screen, (100, 100, 100), (10, 50, 200, 20))
        pygame.draw.rect(self.screen, (0, 200, 0), (10, 50, 200 * fire_cooldown_percent, 20))
        fire_text = self.font.render("Fire Cooldown", True, (255, 255, 255))
        self.screen.blit(fire_text, (10, 30))
        
        # Draw reload indicator
        if reloading:
            reload_progress = min(1.0, (time.time() - reload_start_time) / GameConstants.RELOAD_DURATION)
            pygame.draw.rect(self.screen, (100, 100, 100), (10, 100, 200, 20))
            pygame.draw.rect(self.screen, (0, 100, 255), (10, 100, 200 * reload_progress, 20))
            
            # Show reload time remaining
            time_left = GameConstants.RELOAD_DURATION - (time.time() - reload_start_time)
            reload_text = self.font.render(f"Reloading: {time_left:.1f}s", True, (255, 255, 255))
            self.screen.blit(reload_text, (220, 100))
        else:
            # Draw reload instruction if out of ammo or low ammo
            if ammo_count == 0 and not game_over:
                reload_text = self.font.render("Press R to reload (7s)", True, (255, 255, 0))
                self.screen.blit(reload_text, (10, 80))
            elif ammo_count <= 3 and not game_over:
                reload_text = self.font.render("Low ammo! Press R to reload", True, (255, 165, 0))
                self.screen.blit(reload_text, (10, 80))

    def draw_game_over(self, winner_id, waiting_for_restart):
        """Vẽ màn hình game over"""
        # Semi-transparent overlay
        overlay = pygame.Surface((GameConstants.SCREEN_WIDTH, GameConstants.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Determine winner text
        if winner_id == self.player_id:
            winner_text = self.big_font.render("VICTORY!", True, (0, 255, 0))
        elif winner_id is None:
            winner_text = self.big_font.render("DRAW GAME!", True, (255, 255, 0))
        else:
            winner_text = self.big_font.render("DEFEAT!", True, (255, 0, 0))
        
        text_rect = winner_text.get_rect(center=(400, 250))
        self.screen.blit(winner_text, text_rect)
        
        # Show restart instruction
        if waiting_for_restart:
            restart_text = self.font.render("Waiting for other players...", True, (255, 255, 255))
        else:
            restart_text = self.font.render("Press T to play again", True, (255, 255, 255))
        
        restart_rect = restart_text.get_rect(center=(400, 350))
        self.screen.blit(restart_text, restart_rect)

    def update_display(self):
        """Cập nhật màn hình"""
        pygame.display.flip()

    def cleanup(self):
        """Dọn dẹp pygame"""
        pygame.quit()