-- Enhanced Database Schema for SPX Level-to-Level Movement Tracking
-- Fixed version with proper SQLite syntax

-- 1. SPX PRICE TICKS - Store every SPX price update
CREATE TABLE IF NOT EXISTS spx_price_ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL UNIQUE,
    price REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    volume INTEGER DEFAULT 0,
    session_date TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_spx_ticks_session ON spx_price_ticks(session_date);
CREATE INDEX IF NOT EXISTS idx_spx_ticks_price ON spx_price_ticks(price);
CREATE INDEX IF NOT EXISTS idx_spx_ticks_time ON spx_price_ticks(timestamp);

-- 2. ATR LEVEL CALCULATIONS - Store calculated levels per timeframe
CREATE TABLE IF NOT EXISTS atr_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timeframe TEXT NOT NULL,
    session_date TEXT NOT NULL,
    calculation_time TEXT NOT NULL,
    previous_close REAL NOT NULL,
    atr_value REAL NOT NULL,
    
    -- All 20 ATR levels
    lower_trigger REAL NOT NULL,      -- 0.236 bear
    upper_trigger REAL NOT NULL,      -- 0.236 bull
    lower_0382 REAL NOT NULL,         -- Golden Gate Start (bear)
    upper_0382 REAL NOT NULL,         -- Golden Gate Start (bull)
    lower_0500 REAL NOT NULL,         -- Mid-point (bear)
    upper_0500 REAL NOT NULL,         -- Mid-point (bull)
    lower_0618 REAL NOT NULL,         -- Golden Gate Complete (bear)
    upper_0618 REAL NOT NULL,         -- Golden Gate Complete (bull)
    lower_0786 REAL NOT NULL,         -- Extended (bear)
    upper_0786 REAL NOT NULL,         -- Extended (bull)
    lower_1000 REAL NOT NULL,         -- Full ATR (bear)
    upper_1000 REAL NOT NULL,         -- Full ATR (bull)
    lower_1236 REAL NOT NULL,         -- Extension 1 (bear)
    upper_1236 REAL NOT NULL,         -- Extension 1 (bull)
    lower_1618 REAL NOT NULL,         -- Extension 2 (bear)
    upper_1618 REAL NOT NULL,         -- Extension 2 (bull)
    lower_2000 REAL NOT NULL,         -- Double ATR (bear)
    upper_2000 REAL NOT NULL,         -- Double ATR (bull)
    
    UNIQUE(timeframe, session_date)
);

CREATE INDEX IF NOT EXISTS idx_atr_levels_timeframe ON atr_levels(timeframe);
CREATE INDEX IF NOT EXISTS idx_atr_levels_session ON atr_levels(session_date);

-- 3. LEVEL HITS - Core table for your level-to-level tracking
CREATE TABLE IF NOT EXISTS level_hits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hit_time TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    level_name TEXT NOT NULL,
    level_value REAL NOT NULL,
    hit_price REAL NOT NULL,
    direction TEXT NOT NULL,           -- 'bull' or 'bear'
    fib_ratio REAL NOT NULL,          -- 0.382, 0.618, etc.
    previous_close REAL NOT NULL,
    atr_value REAL NOT NULL,
    session_date TEXT NOT NULL,
    
    -- Movement tracking fields
    next_level_hit_id INTEGER,
    movement_time_seconds INTEGER,
    movement_direction TEXT,
    levels_moved INTEGER,
    
    FOREIGN KEY (next_level_hit_id) REFERENCES level_hits(id)
);

CREATE INDEX IF NOT EXISTS idx_level_hits_time ON level_hits(hit_time);
CREATE INDEX IF NOT EXISTS idx_level_hits_timeframe ON level_hits(timeframe);
CREATE INDEX IF NOT EXISTS idx_level_hits_level ON level_hits(level_name);
CREATE INDEX IF NOT EXISTS idx_level_hits_session ON level_hits(session_date);
CREATE INDEX IF NOT EXISTS idx_level_hits_direction ON level_hits(direction);
CREATE INDEX IF NOT EXISTS idx_level_hits_fib_ratio ON level_hits(fib_ratio);

-- 4. GOLDEN GATE TRACKING - Special tracking for .382 -> .618 movements
CREATE TABLE IF NOT EXISTS golden_gate_sequences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timeframe TEXT NOT NULL,
    direction TEXT NOT NULL,
    session_date TEXT NOT NULL,
    
    -- Start (.382 level hit)
    start_level_hit_id INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    start_price REAL NOT NULL,
    
    -- Completion (.618 level hit - if it happens)
    complete_level_hit_id INTEGER,
    complete_time TEXT,
    complete_price REAL,
    
    -- Analytics
    completed BOOLEAN DEFAULT FALSE,
    duration_seconds INTEGER,
    price_movement REAL,
    success_probability REAL,
    
    FOREIGN KEY (start_level_hit_id) REFERENCES level_hits(id),
    FOREIGN KEY (complete_level_hit_id) REFERENCES level_hits(id)
);

CREATE INDEX IF NOT EXISTS idx_gg_timeframe ON golden_gate_sequences(timeframe);
CREATE INDEX IF NOT EXISTS idx_gg_direction ON golden_gate_sequences(direction);
CREATE INDEX IF NOT EXISTS idx_gg_session ON golden_gate_sequences(session_date);
CREATE INDEX IF NOT EXISTS idx_gg_completed ON golden_gate_sequences(completed);

-- 5. LEVEL TRANSITION STATISTICS - Pre-calculated analytics
CREATE TABLE IF NOT EXISTS level_transition_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timeframe TEXT NOT NULL,
    from_level TEXT NOT NULL,
    to_level TEXT NOT NULL,
    direction TEXT NOT NULL,
    
    -- Statistics
    total_occurrences INTEGER DEFAULT 0,
    successful_hits INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    avg_time_seconds REAL DEFAULT 0.0,
    min_time_seconds INTEGER,
    max_time_seconds INTEGER,
    
    -- Last updated
    last_calculated TEXT NOT NULL,
    data_points_count INTEGER DEFAULT 0,
    
    UNIQUE(timeframe, from_level, to_level, direction)
);

CREATE INDEX IF NOT EXISTS idx_transition_stats_timeframe ON level_transition_stats(timeframe);
CREATE INDEX IF NOT EXISTS idx_transition_stats_success_rate ON level_transition_stats(success_rate);

-- 6. SESSION SUMMARIES - Daily rollup for performance
CREATE TABLE IF NOT EXISTS daily_session_summary (
    session_date TEXT PRIMARY KEY,
    
    -- Overall activity
    total_ticks_processed INTEGER DEFAULT 0,
    total_level_hits INTEGER DEFAULT 0,
    unique_levels_hit INTEGER DEFAULT 0,
    
    -- By timeframe
    scalp_hits INTEGER DEFAULT 0,
    day_hits INTEGER DEFAULT 0,
    multiday_hits INTEGER DEFAULT 0,
    swing_hits INTEGER DEFAULT 0,
    position_hits INTEGER DEFAULT 0,
    long_term_hits INTEGER DEFAULT 0,
    
    -- Golden Gate activity
    golden_gate_starts INTEGER DEFAULT 0,
    golden_gate_completions INTEGER DEFAULT 0,
    golden_gate_success_rate REAL DEFAULT 0.0,
    
    -- Price range
    session_high REAL,
    session_low REAL,
    session_open REAL,
    session_close REAL,
    
    -- Performance
    avg_processing_time_ms REAL DEFAULT 0.0,
    
    -- Last updated
    last_updated TEXT NOT NULL
);

-- VIEWS for common queries

-- View: Recent Level Hits (last 24 hours)
CREATE VIEW IF NOT EXISTS recent_level_hits AS
SELECT 
    lh.*,
    al.atr_value,
    al.previous_close
FROM level_hits lh
JOIN atr_levels al ON lh.timeframe = al.timeframe AND lh.session_date = al.session_date
WHERE datetime(lh.hit_time) > datetime('now', '-24 hours')
ORDER BY lh.hit_time DESC;

-- View: Active Golden Gate Sequences
CREATE VIEW IF NOT EXISTS active_golden_gates AS
SELECT *
FROM golden_gate_sequences
WHERE completed = FALSE
  AND datetime(start_time) > datetime('now', '-7 days')
ORDER BY start_time DESC;

-- View: Level Hit Frequency by Timeframe
CREATE VIEW IF NOT EXISTS level_hit_frequency AS
SELECT 
    timeframe,
    level_name,
    direction,
    COUNT(*) as hit_count,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM level_hits) as percentage
FROM level_hits
WHERE session_date >= date('now', '-30 days')
GROUP BY timeframe, level_name, direction
ORDER BY hit_count DESC;
