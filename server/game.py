import math
import time
from common.messages import GameConstants

class GameEngine:
    def __init__(self):
        self.players = {}
        self.bullets = []
        self.game_state = {
            'players': {}, 
            'bullets': [], 
            'game_over': False,
            'winner_id': None
        }
        self.ready_players = set()
        self.restart_requests = set()
        self.game_started = False
        self.current_session_id = None
        self.game_start_time = 0
        self.player_stats = {}  # Theo dõi thống kê player
        self.current_map = 0  # Map hiện tại

    def add_player(self, player_id, udp_address, tcp_socket):
        """Thêm player mới vào game"""
        self.players[player_id] = {
            'tcp_socket': tcp_socket,
            'udp_address': udp_address,
            'x': 100 if player_id == '1' else 700,
            'y': 300,
            'angle': 0,
            'hp': GameConstants.PLAYER_HP,
            'ammo': GameConstants.MAX_AMMO,
            'ready': False
        }
        
        # Khởi tạo stats
        self.player_stats[player_id] = {
            'damage_dealt': 0,
            'shots_fired': 0,
            'shots_hit': 0,
            'reloads_count': 0,
            'survival_time': 0
        }

    def process_player_message(self, player_id, message):
        """Xử lý message từ player và cập nhật thống kê"""
        player = self.players[player_id]
        
        # Cập nhật vị trí - SỬA LẠI ĐỂ NHẬN DI CHUYỂN TỪ CLIENT
        if 'x' in message and 'y' in message and 'angle' in message:
            player['x'] = max(20, min(GameConstants.SCREEN_WIDTH - 20, message['x']))
            player['y'] = max(20, min(GameConstants.SCREEN_HEIGHT - 20, message['y']))
            player['angle'] = message['angle']
        
        # Xử lý bắn đạn
        if message.get('fire') and player['ammo'] > 0 and not self.game_state['game_over']:
            player['ammo'] -= 1
            self.bullets.append({
                'x': player['x'],
                'y': player['y'],
                'angle': player['angle'],
                'speed': GameConstants.BULLET_SPEED,
                'owner': player_id
            })
            self.player_stats[player_id]['shots_fired'] += 1
        
        # Xử lý reload
        if message.get('reload'):
            player['ammo'] = GameConstants.MAX_AMMO
            self.player_stats[player_id]['reloads_count'] += 1
        
        # Cập nhật ammo
        if 'ammo_update' in message:
            player['ammo'] = message['ammo_update']

    def _check_collisions(self):
        """Kiểm tra va chạm đạn với người chơi và theo dõi sát thương"""
        for bullet in self.bullets[:]:
            for pid, player in self.players.items():
                if pid != bullet['owner']:
                    distance = math.sqrt((bullet['x'] - player['x'])**2 + 
                                       (bullet['y'] - player['y'])**2)
                    if distance < 25:  # Va chạm
                        player['hp'] -= GameConstants.BULLET_DAMAGE
                        
                        # Cập nhật thống kê (damage, hits)
                        owner_stats = self.player_stats[bullet['owner']]
                        owner_stats['damage_dealt'] += GameConstants.BULLET_DAMAGE
                        owner_stats['shots_hit'] += 1
                        
                        if bullet in self.bullets:
                            self.bullets.remove(bullet)
                        
                        # Kiểm tra game over
                        if player['hp'] <= 0:
                            self._end_game(winner_id=bullet['owner'])
                        break

    def get_player_stats(self, player_id):
        """Lấy thống kê của player"""
        if player_id not in self.player_stats:
            return None
            
        stats = self.player_stats[player_id].copy()
        stats['final_hp'] = self.players[player_id]['hp']
        stats['survival_time'] = int(time.time() - self.game_start_time)
        
        return stats

    def get_player_score(self, player_id):
        """Tính điểm cho player"""
        if player_id not in self.player_stats:
            return 0
            
        stats = self.player_stats[player_id]
        score = (stats['damage_dealt'] * 2 + 
                stats['shots_hit'] * 10 + 
                self.players[player_id]['hp'])
        return score

    

    def remove_player(self, player_id):
        """Xóa player khỏi game"""
        if player_id in self.players:
            del self.players[player_id]
            self.ready_players.discard(player_id)
            self.restart_requests.discard(player_id)

    def set_player_ready(self, player_id):
        """Đánh dấu player đã ready"""
        if player_id in self.players:
            self.players[player_id]['ready'] = True
            self.ready_players.add(player_id)

    def check_game_start(self):
        """Kiểm tra điều kiện bắt đầu game"""
        return len(self.ready_players) >= GameConstants.MAX_PLAYERS and not self.game_started

    def start_game(self):
        """Bắt đầu game mới"""
        self.game_started = True
        self.restart_requests.clear()
        self.game_state['game_over'] = False
        self.game_state['winner_id'] = None

    
    def update_game(self):
        """Cập nhật logic game chính"""
        if self.game_started and not self.game_state['game_over']:
            self._update_bullets()
            self._check_collisions()
            self._update_game_state()

    def _update_bullets(self):
        """Cập nhật vị trí đạn và kiểm tra va chạm tường"""
        for bullet in self.bullets[:]:
            bullet['x'] += bullet['speed'] * math.cos(math.radians(bullet['angle']))
            bullet['y'] += bullet['speed'] * math.sin(math.radians(bullet['angle']))
            
            # Kiểm tra va chạm tường
            if (bullet['x'] < 0 or bullet['x'] > GameConstants.SCREEN_WIDTH or 
                bullet['y'] < 0 or bullet['y'] > GameConstants.SCREEN_HEIGHT):
                self.bullets.remove(bullet)

    
    def _end_game(self, winner_id):
        """Kết thúc game"""
        self.game_started = False
        self.game_state['game_over'] = True
        self.game_state['winner_id'] = winner_id

    def _update_game_state(self):
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

    def handle_restart_request(self, player_id):
        """Xử lý yêu cầu restart từ player"""
        self.restart_requests.add(player_id)
        return len(self.restart_requests) >= GameConstants.MAX_PLAYERS

    def restart_game(self):
        """Khởi động lại game"""
        self.game_started = False
        self.ready_players.clear()
        self.restart_requests.clear()
        self.bullets.clear()
        self.game_state['game_over'] = False
        self.game_state['winner_id'] = None
        self.player_stats.clear()
        self.current_session_id = None
        
        # Reset player positions và stats
        for pid, player in self.players.items():
            player['x'] = 100 if pid == '1' else 700
            player['y'] = 300
            player['angle'] = 0
            player['hp'] = GameConstants.PLAYER_HP
            player['ammo'] = GameConstants.MAX_AMMO
            player['ready'] = False

    def get_game_state(self):
        """Lấy current game state"""
        return self.game_state

    def get_player_udp_address(self, player_id):
        """Lấy UDP address của player"""
        return self.players[player_id]['udp_address'] if player_id in self.players else None

    def get_all_tcp_sockets(self):
        """Lấy tất cả TCP sockets của players"""
        return [player['tcp_socket'] for player in self.players.values()]