import socket
import threading
import json
import time
from server.game import GameEngine
from server.database_manager_pymysql import DatabaseManager  # Đổi import này
from common.messages import MessageTypes, GameConstants

class TankServer:
    def __init__(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host = '0.0.0.0'
        self.tcp_port = GameConstants.TCP_PORT
        self.udp_port = GameConstants.UDP_PORT
        self.game_engine = GameEngine()
        self.database = DatabaseManager()  # Sẽ sử dụng PyMySQL
        self.running = True
        self.player_authenticated = {}
        self.game_sessions = {}
        
    
