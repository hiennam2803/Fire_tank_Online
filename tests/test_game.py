import unittest
import sys
import os

# Thêm path để import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from server.game import GameEngine

class TestGameEngine(unittest.TestCase):
    def setUp(self):
        self.game = GameEngine()
    
    def test_add_player(self):
        self.game.add_player('1', ('127.0.0.1', 12345), None)
        self.assertIn('1', self.game.players)
        self.assertEqual(self.game.players['1']['x'], 100)
        self.assertEqual(self.game.players['1']['hp'], 100)
    
    def test_player_ready(self):
        self.game.add_player('1', ('127.0.0.1', 12345), None)
        self.game.set_player_ready('1')
        self.assertTrue(self.game.players['1']['ready'])
        self.assertIn('1', self.game.ready_players)
    
    def test_game_start_condition(self):
        self.game.add_player('1', ('127.0.0.1', 12345), None)
        self.game.add_player('2', ('127.0.0.1', 12346), None)
        
        self.game.set_player_ready('1')
        self.assertFalse(self.game.check_game_start())
        
        self.game.set_player_ready('2')
        self.assertTrue(self.game.check_game_start())

if __name__ == '__main__':
    unittest.main()