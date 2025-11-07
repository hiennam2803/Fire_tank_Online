import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py [server|client]")
        return

    mode = sys.argv[1]
    
    if mode == "server":
        from server.server import TankServer
        server = TankServer()
        server.start()
    elif mode == "client":
        from client.client import TankGame
        game = TankGame()
        game.connect()
        game.run()
    else:
        print("Invalid mode. Use 'server' or 'client'")

if __name__ == "__main__":
    main()