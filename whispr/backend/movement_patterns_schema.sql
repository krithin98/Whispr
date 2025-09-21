-- Movement patterns and transition statistics tables

-- Table for storing detected patterns
CREATE TABLE IF NOT EXISTS movement_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detection_time TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    from_level TEXT NOT NULL,
    to_level TEXT NOT NULL,
    from_hit_id INTEGER,
    to_hit_id INTEGER,
    duration_seconds REAL,
    price_change REAL,
    session_date TEXT DEFAULT (DATE('now')),
    FOREIGN KEY (from_hit_id) REFERENCES level_hits(id),
    FOREIGN KEY (to_hit_id) REFERENCES level_hits(id)
);

-- Table for aggregated transition statistics
CREATE TABLE IF NOT EXISTS level_transition_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timeframe TEXT NOT NULL,
    from_level TEXT NOT NULL,
    to_level TEXT NOT NULL,
    transition_count INTEGER DEFAULT 0,
    success_rate REAL,  -- Percentage of times this transition completes
    avg_duration_seconds REAL,
    min_duration_seconds REAL,
    max_duration_seconds REAL,
    avg_price_change REAL,
    avg_velocity REAL,  -- Average levels per minute
    last_occurrence TEXT,
    calculation_date TEXT DEFAULT (DATE('now')),
    UNIQUE(timeframe, from_level, to_level, calculation_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_movement_patterns_timeframe ON movement_patterns(timeframe);
CREATE INDEX IF NOT EXISTS idx_movement_patterns_pattern ON movement_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_movement_patterns_session ON movement_patterns(session_date);

CREATE INDEX IF NOT EXISTS idx_transition_stats_timeframe ON level_transition_stats(timeframe);
CREATE INDEX IF NOT EXISTS idx_transition_stats_levels ON level_transition_stats(from_level, to_level);