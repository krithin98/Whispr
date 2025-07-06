import aiosqlite
import json
import os
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "/app/data/seer.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # /app/data

CREATE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    payload     TEXT
);
"""

CREATE_STRATEGIES_TABLE = """
CREATE TABLE IF NOT EXISTS strategies (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    strategy_expression TEXT NOT NULL,  -- e.g. "GG Day Bull Trigger" or "price > 105"
    prompt_tpl   TEXT NOT NULL,     -- templated text for the LLM
    is_active    INTEGER DEFAULT 1,
    tags         TEXT,              -- JSON array of tags
    priority     INTEGER DEFAULT 5,
    strategy_type    TEXT DEFAULT 'standard',  -- 'standard', 'golden_gate', 'indicator_based'
    indicator_ref TEXT,             -- e.g. "saty_atr_levels" or null for direct expressions
    indicator_params TEXT           -- JSON object with indicator-specific parameters
);
"""

CREATE_SIM_TRADES_TABLE = """
CREATE TABLE IF NOT EXISTS sim_trades (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT NOT NULL,
    side         TEXT NOT NULL,   -- 'buy' or 'sell'
    quantity     INTEGER NOT NULL,
    entry_price  REAL NOT NULL,
    exit_price   REAL,
    entry_time   TEXT NOT NULL,
    exit_time    TEXT,
    status       TEXT NOT NULL,   -- 'open', 'closed', 'cancelled'
    pnl          REAL,
    pnl_percent  REAL
);
"""

CREATE_INDICATORS_TABLE = """
CREATE TABLE IF NOT EXISTS indicators (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,  -- e.g. "saty_atr_levels"
    indicator_type TEXT NOT NULL,       -- e.g. "atr_levels", "moving_average", "rsi"
    config       TEXT NOT NULL,         -- JSON configuration
    is_active    INTEGER DEFAULT 1,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDICATOR_DATA_TABLE = """
CREATE TABLE IF NOT EXISTS indicator_data (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id INTEGER NOT NULL,
    symbol       TEXT NOT NULL,
    timeframe    TEXT NOT NULL,         -- e.g. "day", "week", "month"
    timestamp    TEXT NOT NULL,
    data         TEXT NOT NULL,         -- JSON object with calculated values
    FOREIGN KEY (indicator_id) REFERENCES indicators(id)
);
"""

CREATE_STRATEGY_STATES_TABLE = """
CREATE TABLE IF NOT EXISTS strategy_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,
    timeframe TEXT NOT NULL,
    side TEXT NOT NULL,
    event_type TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    triggered_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);
"""

CREATE_GG_STATE_TABLE = """
CREATE TABLE IF NOT EXISTS gg_state (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timeframe    TEXT NOT NULL,   -- 'scalp', 'day', 'multiday', 'swing', 'position', 'long_term'
    side         TEXT NOT NULL,   -- 'bull' or 'bear'
    trigger_active INTEGER DEFAULT 0,  -- 0 or 1
    trigger_price REAL,
    trigger_time TEXT,
    completed    INTEGER DEFAULT 0,    -- 0 or 1
    complete_price REAL,
    complete_time TEXT,
    session_date TEXT NOT NULL,   -- YYYY-MM-DD for daily reset
    UNIQUE(timeframe, side, session_date)
);
"""

CREATE_GG_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS gg_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT NOT NULL,   -- ISO8601
    rule_name    TEXT NOT NULL,
    price        REAL NOT NULL,
    timeframe    TEXT NOT NULL,
    event_type   TEXT NOT NULL,   -- 'trigger' or 'complete'
    side         TEXT NOT NULL,   -- 'bull' or 'bear'
    session_date TEXT NOT NULL
);
"""

async def get_db():
    """Return a singleton connection (FastAPI will reuse it)."""
    if not hasattr(get_db, "conn"):
        get_db.conn = await aiosqlite.connect(DB_PATH, isolation_level=None)  # autocommit
        # Create tables separately
        await get_db.conn.execute(CREATE_EVENTS_TABLE)
        await get_db.conn.execute(CREATE_STRATEGIES_TABLE)
        await get_db.conn.execute(CREATE_SIM_TRADES_TABLE)
        await get_db.conn.execute(CREATE_INDICATORS_TABLE)
        await get_db.conn.execute(CREATE_INDICATOR_DATA_TABLE)
        await get_db.conn.execute(CREATE_STRATEGY_STATES_TABLE)
    return get_db.conn

async def log_event(event_type: str, payload: dict):
    conn = await get_db()
    await conn.execute(
        "INSERT INTO events (ts, event_type, payload) VALUES (datetime('now'), ?, ?)",
        (event_type, json.dumps(payload)),
    ) 