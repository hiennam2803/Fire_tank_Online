CREATE DATABASE IF NOT EXISTS tank_battle;
USE tank_battle;

CREATE TABLE IF NOT EXISTS players (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    games_played INT DEFAULT 0,
    games_won INT DEFAULT 0,
    total_damage_dealt INT DEFAULT 0,
    total_shots_fired INT DEFAULT 0,
    accuracy DECIMAL(5,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS game_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_code VARCHAR(10) UNIQUE NOT NULL,
    map_id INT DEFAULT 1,
    player1_id INT,
    player2_id INT,
    winner_id INT NULL,
    duration_seconds INT DEFAULT 0,
    player1_score INT DEFAULT 0,
    player2_score INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player1_id) REFERENCES players(id),
    FOREIGN KEY (player2_id) REFERENCES players(id),
    FOREIGN KEY (winner_id) REFERENCES players(id)
);

CREATE TABLE IF NOT EXISTS player_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    player_id INT NOT NULL,
    game_session_id INT NOT NULL,
    final_hp INT DEFAULT 0,
    damage_dealt INT DEFAULT 0,
    shots_fired INT DEFAULT 0,
    shots_hit INT DEFAULT 0,
    reloads_count INT DEFAULT 0,
    survival_time INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (game_session_id) REFERENCES game_sessions(id)
);

-- Thêm index để tối ưu truy vấn
CREATE INDEX idx_players_username ON players(username);
CREATE INDEX idx_game_sessions_created ON game_sessions(created_at);
CREATE INDEX idx_player_stats_player ON player_stats(player_id);