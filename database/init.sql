-- Pokemon Showdown LLM Battle Service Database Schema
-- Initialize database with tables for production use

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS pokemon_showdown;
\c pokemon_showdown;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Bot configurations table
CREATE TABLE IF NOT EXISTS bot_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    battle_format VARCHAR(100) NOT NULL DEFAULT 'gen9randombattle',
    llm_provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(255),
    use_mock_llm BOOLEAN DEFAULT FALSE,
    max_concurrent_battles INTEGER DEFAULT 1,
    custom_config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bot statistics table
CREATE TABLE IF NOT EXISTS bot_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    elo_rating DECIMAL(10,2) DEFAULT 1200.0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    total_battles INTEGER DEFAULT 0,
    win_rate DECIMAL(5,4) DEFAULT 0.0,
    longest_win_streak INTEGER DEFAULT 0,
    current_win_streak INTEGER DEFAULT 0,
    last_battle_time TIMESTAMP WITH TIME ZONE,
    battle_formats JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (username) REFERENCES bot_configs(username) ON DELETE CASCADE
);

-- Battle results table
CREATE TABLE IF NOT EXISTS battle_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    battle_id VARCHAR(255) UNIQUE NOT NULL,
    bot1_username VARCHAR(255) NOT NULL,
    bot2_username VARCHAR(255) NOT NULL,
    winner VARCHAR(255),
    battle_format VARCHAR(100) NOT NULL,
    duration DECIMAL(10,3) DEFAULT 0.0,
    turns INTEGER DEFAULT 0,
    battle_log TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    server_url VARCHAR(255),
    replay_url VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (bot1_username) REFERENCES bot_configs(username),
    FOREIGN KEY (bot2_username) REFERENCES bot_configs(username)
);

-- Battle queue table for async processing
CREATE TABLE IF NOT EXISTS battle_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot1_username VARCHAR(255) NOT NULL,
    bot2_username VARCHAR(255) NOT NULL,
    battle_format VARCHAR(100) NOT NULL,
    priority INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tournament configurations table
CREATE TABLE IF NOT EXISTS tournaments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    tournament_type VARCHAR(50) NOT NULL, -- round_robin, single_elimination, etc.
    battle_format VARCHAR(100) NOT NULL,
    max_participants INTEGER DEFAULT 8,
    status VARCHAR(50) DEFAULT 'planned', -- planned, active, completed, cancelled
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    winner VARCHAR(255),
    participants JSONB DEFAULT '[]',
    configuration JSONB DEFAULT '{}',
    results JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- System metrics table for monitoring
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(255) NOT NULL,
    metric_value DECIMAL(15,6) NOT NULL,
    labels JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_battle_results_timestamp ON battle_results(timestamp);
CREATE INDEX IF NOT EXISTS idx_battle_results_format ON battle_results(battle_format);
CREATE INDEX IF NOT EXISTS idx_battle_results_bot1 ON battle_results(bot1_username);
CREATE INDEX IF NOT EXISTS idx_battle_results_bot2 ON battle_results(bot2_username);
CREATE INDEX IF NOT EXISTS idx_battle_results_winner ON battle_results(winner);

CREATE INDEX IF NOT EXISTS idx_bot_stats_elo ON bot_stats(elo_rating);
CREATE INDEX IF NOT EXISTS idx_bot_stats_wins ON bot_stats(wins);
CREATE INDEX IF NOT EXISTS idx_bot_stats_winrate ON bot_stats(win_rate);

CREATE INDEX IF NOT EXISTS idx_battle_queue_status ON battle_queue(status);
CREATE INDEX IF NOT EXISTS idx_battle_queue_scheduled ON battle_queue(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_battle_queue_priority ON battle_queue(priority);

CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);

-- Create views for common queries
CREATE OR REPLACE VIEW leaderboard_view AS
SELECT 
    bs.username,
    bs.elo_rating,
    bs.wins,
    bs.losses,
    bs.draws,
    bs.total_battles,
    bs.win_rate,
    bs.longest_win_streak,
    bs.current_win_streak,
    bs.last_battle_time,
    bc.llm_provider,
    bc.model_name,
    bc.battle_format as default_format,
    bc.is_active
FROM bot_stats bs
JOIN bot_configs bc ON bs.username = bc.username
WHERE bc.is_active = TRUE
ORDER BY bs.elo_rating DESC;

CREATE OR REPLACE VIEW recent_battles_view AS
SELECT 
    br.battle_id,
    br.bot1_username,
    br.bot2_username,
    br.winner,
    br.battle_format,
    br.duration,
    br.turns,
    br.timestamp,
    bc1.llm_provider as bot1_provider,
    bc1.model_name as bot1_model,
    bc2.llm_provider as bot2_provider,
    bc2.model_name as bot2_model
FROM battle_results br
JOIN bot_configs bc1 ON br.bot1_username = bc1.username
JOIN bot_configs bc2 ON br.bot2_username = bc2.username
ORDER BY br.timestamp DESC;

-- Function to update bot stats after battle
CREATE OR REPLACE FUNCTION update_bot_stats_after_battle()
RETURNS TRIGGER AS $$
BEGIN
    -- Update stats for bot1
    UPDATE bot_stats 
    SET 
        total_battles = total_battles + 1,
        wins = CASE WHEN NEW.winner = NEW.bot1_username THEN wins + 1 ELSE wins END,
        losses = CASE WHEN NEW.winner = NEW.bot2_username THEN losses + 1 ELSE losses END,
        draws = CASE WHEN NEW.winner IS NULL THEN draws + 1 ELSE draws END,
        last_battle_time = NEW.timestamp,
        updated_at = NOW()
    WHERE username = NEW.bot1_username;
    
    -- Update stats for bot2
    UPDATE bot_stats 
    SET 
        total_battles = total_battles + 1,
        wins = CASE WHEN NEW.winner = NEW.bot2_username THEN wins + 1 ELSE wins END,
        losses = CASE WHEN NEW.winner = NEW.bot1_username THEN losses + 1 ELSE losses END,
        draws = CASE WHEN NEW.winner IS NULL THEN draws + 1 ELSE draws END,
        last_battle_time = NEW.timestamp,
        updated_at = NOW()
    WHERE username = NEW.bot2_username;
    
    -- Recalculate win rates
    UPDATE bot_stats 
    SET win_rate = CASE 
        WHEN total_battles = 0 THEN 0.0 
        ELSE ROUND(wins::DECIMAL / total_battles::DECIMAL, 4) 
    END
    WHERE username IN (NEW.bot1_username, NEW.bot2_username);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update stats
CREATE TRIGGER update_bot_stats_trigger
    AFTER INSERT ON battle_results
    FOR EACH ROW
    EXECUTE FUNCTION update_bot_stats_after_battle();

-- Function to clean old system metrics (keep last 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_metrics()
RETURNS void AS $$
BEGIN
    DELETE FROM system_metrics 
    WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Insert default system configuration
INSERT INTO bot_configs (username, battle_format, llm_provider, model_name, use_mock_llm, is_active) VALUES
('system-health-check', 'gen9randombattle', 'mock', 'health-check-bot', TRUE, FALSE)
ON CONFLICT (username) DO NOTHING;

INSERT INTO bot_stats (username, elo_rating) VALUES
('system-health-check', 1200.0)
ON CONFLICT (username) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO psuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO psuser;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO psuser;

COMMIT;