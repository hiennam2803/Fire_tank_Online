# Định nghĩa các message type và constants
class MessageTypes:
    # TCP Messages
    READY = "READY"
    RESTART = "RESTART"
    GAME_START = "GAME_START"
    WAITING_FOR_PLAYERS = "WAITING_FOR_PLAYERS"
    SERVER_FULL = "SERVER_FULL"
    RESTART_ACCEPTED = "RESTART_ACCEPTED"
    
    # UDP Message keys
    PLAYER_UPDATE = 'player_update'
    FIRE = 'fire'
    RELOAD = 'reload'
    AMMO_UPDATE = 'ammo_update'

class GameConstants:
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 600
    TCP_PORT = 5555
    UDP_PORT = 5556
    MAX_PLAYERS = 2
    FIRE_COOLDOWN = 0.5
    RELOAD_DURATION = 7.0
    MAX_AMMO = 10
    PLAYER_HP = 100
    BULLET_SPEED = 10
    BULLET_DAMAGE = 25