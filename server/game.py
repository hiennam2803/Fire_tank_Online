import math
import time
import random 
from common.messages import GameConstants

class GameEngine:
    def __init__(self):
        self.players = {}
        self.bullets = []
        self.game_state = {
            'players': {}, 
            'bullets': [], 
            'game_over': False,
            'winner_id': None,
            'map_id': 0 
        }
        self.ready_players = set()
        self.restart_requests = set()
        self.game_started = False
        self.current_session_id = None
        self.game_start_time = 0
        self.player_stats = {}  # Theo dõi thống kê player
        
        # Random map ngay khi khởi tạo
        self.current_map = random.randint(0, GameConstants.MAP_COUNT - 1)
        self.game_state['map_id'] = self.current_map


    def add_player(self, player_id, udp_address, tcp_socket, player_name="Player"):
        """Thêm player mới vào game"""
        
        # Spawn player dựa trên SỐ LƯỢNG player
        spawn_x = 100 if len(self.players) == 0 else 700
        
        self.players[player_id] = {
            'tcp_socket': tcp_socket,
            'udp_address': udp_address,
            'x': spawn_x, 
            'y': 300,
            'angle': 0,
            'hp': GameConstants.PLAYER_HP,
            'ammo': GameConstants.MAX_AMMO,
            'ready': False,
            'name': f"{player_name} ({player_id})" 
        }
        
        # Khởi tạo stats
        self.player_stats[player_id] = {
            'damage_dealt': 0,
            'shots_fired': 0,
            'shots_hit': 0,
            'reloads_count': 0,
            'survival_time': 0
        }
        
    def update_player_name(self, player_id, name):
        """Cập nhật tên người chơi sau khi xác thực"""
        if player_id in self.players:
            self.players[player_id]['name'] = name


    def process_player_message(self, player_id, message):
        """Xử lý message từ player và cập nhật thống kê"""
        if player_id not in self.players:
             return 
        
        player = self.players[player_id]
        
        # Cập nhật vị trí
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
            if player_id in self.player_stats: 
                self.player_stats[player_id]['shots_fired'] += 1
        
        # Xử lý reload (do client tự quản lý)
        if message.get('reload'):
            if player_id in self.player_stats:
                self.player_stats[player_id]['reloads_count'] += 1
        
        # Cập nhật ammo (khi client reload xong)
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
                        
                        owner = bullet.get('owner')
                        if owner in self.player_stats:
                            owner_stats = self.player_stats[owner]
                            owner_stats['damage_dealt'] += GameConstants.BULLET_DAMAGE
                            owner_stats['shots_hit'] += 1
                        
                        if bullet in self.bullets:
                            self.bullets.remove(bullet)
                        
                        if player['hp'] <= 0:
                            self._end_game(winner_id=bullet['owner'])
                        break 

    def get_player_stats(self, player_id):
        """Lấy thống kê của player"""
        if player_id not in self.player_stats:
            self.player_stats[player_id] = { 'damage_dealt': 0, 'shots_fired': 0, 'shots_hit': 0, 'reloads_count': 0, 'survival_time': 0 }
            
        stats = self.player_stats[player_id].copy()
        
        if player_id in self.players:
            stats['final_hp'] = self.players[player_id]['hp']
        else:
            stats['final_hp'] = 0 
            
        if self.game_started or self.game_state['game_over']:
            stats['survival_time'] = int(time.time() - self.game_start_time)
        else:
            stats['survival_time'] = 0

        return stats

    def get_player_score(self, player_id):
        """Tính điểm cho player"""
        if player_id not in self.player_stats or player_id not in self.players:
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
        if player_id in self.player_stats:
            del self.player_stats[player_id] 
            
        self.ready_players.discard(player_id)
        self.restart_requests.discard(player_id)
        
        if self.game_started and len(self.players) < GameConstants.MAX_PLAYERS:
            print(f"Player {player_id} disconnected. Ending game.")
            opponent = list(self.players.keys())[0] if self.players else None
            self._end_game(winner_id=opponent) 
        elif not self.game_started:
             print(f"Player {player_id} disconnected from lobby.")


    def set_player_ready(self, player_id):
        """Đánh dấu player đã ready"""
        if player_id in self.players:
            self.players[player_id]['ready'] = True
            self.ready_players.add(player_id)
            print(f"Players ready: {self.ready_players}") 

    def check_game_start(self):
        """Kiểm tra điều kiện bắt đầu game"""
        all_players_ready = (len(self.ready_players) == len(self.players))
        
        return (len(self.players) >= GameConstants.MAX_PLAYERS and
                all_players_ready and
                not self.game_started)

    def start_game(self):
        """Bắt đầu game mới"""
        self.game_started = True
        self.restart_requests.clear()
        self.game_state['game_over'] = False
        self.game_state['winner_id'] = None
        self.game_start_time = time.time() # Đặt thời gian bắt đầu
        print("GameEngine: Game is starting!")

    
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
            
            if (bullet['x'] < 0 or bullet['x'] > GameConstants.SCREEN_WIDTH or 
                bullet['y'] < 0 or bullet['y'] > GameConstants.SCREEN_HEIGHT):
                if bullet in self.bullets:
                    self.bullets.remove(bullet)

    
    def _end_game(self, winner_id):
        """Kết thúc game"""
        if self.game_state['game_over']: 
             return
        print(f"Game ending. Winner: {winner_id}")
        self.game_started = False
        self.game_state['game_over'] = True
        self.game_state['winner_id'] = winner_id
        
        # Cập nhật stats lần cuối
        for pid in self.players.keys():
            if pid in self.player_stats:
                self.player_stats[pid]['survival_time'] = int(time.time() - self.game_start_time)


    def _update_game_state(self):
        """Cập nhật game state từ player data"""
        self.game_state['players'] = {}
        for pid, player in self.players.items():
            self.game_state['players'][pid] = {
                'x': player['x'],
                'y': player['y'], 
                'angle': player['angle'],
                'hp': player['hp'],
                'ammo': player['ammo'],
                'name': player.get('name', f"Player {pid}"), 
                'ready': player.get('ready', False) 
            }
        self.game_state['bullets'] = self.bullets.copy()
        self.game_state['map_id'] = self.current_map

    def handle_restart_request(self, player_id):
        """Xử lý yêu cầu restart từ player"""
        self.restart_requests.add(player_id)
        return len(self.restart_requests) >= len(self.players) and len(self.players) > 0


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
        
        # === SỬA LỖI LOGIC: CHỌN MAP MỚI KHÁC MAP CŨ ===
        old_map = self.current_map
        # Tạo danh sách các map có thể chọn (không bao gồm map cũ)
        possible_maps = [i for i in range(GameConstants.MAP_COUNT) if i != old_map]
        
        if not possible_maps: # Trường hợp chỉ có 1 map
            self.current_map = old_map
        else:
            self.current_map = random.choice(possible_maps)
            
        self.game_state['map_id'] = self.current_map
        print(f"Game restarting. Old map was {old_map}, new map is {self.current_map}")
        # === KẾT THÚC SỬA ===
        
        # Đặt lại vị trí và số liệu thống kê của người chơi
        player_count = 0
        for pid, player in self.players.items():
            player['x'] = 100 if player_count == 0 else 700 
            player['y'] = 300
            player['angle'] = 0
            player['hp'] = GameConstants.PLAYER_HP
            player['ammo'] = GameConstants.MAX_AMMO
            player['ready'] = False
            player_count += 1
            
            # Tạo lại số liệu thống kê
            self.player_stats[pid] = {
                'damage_dealt': 0,
                'shots_fired': 0,
                'shots_hit': 0,
                'reloads_count': 0,
                'survival_time': 0
            }

    def get_game_state(self):
        """Lấy current game state"""
        return self.game_state

    def get_player_udp_address(self, player_id):
        """Lấy UDP address của player"""
        return self.players[player_id]['udp_address'] if player_id in self.players else None

    def get_all_tcp_sockets(self):
        """Lấy tất cả TCP sockets của players"""
        return [player['tcp_socket'] for player in self.players.values()]