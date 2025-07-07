import aiosqlite
import json
import os
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "./data/seer.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # ./data

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

CREATE_STRATEGY_TRIGGERS_TABLE = """
CREATE TABLE IF NOT EXISTS strategy_triggers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id  INTEGER NOT NULL,
    strategy_name TEXT NOT NULL,
    strategy_type TEXT NOT NULL,
    symbol       TEXT NOT NULL,
    timeframe    TEXT NOT NULL,
    trigger_type TEXT NOT NULL,   -- 'entry', 'exit', 'signal', 'alert'
    side         TEXT,            -- 'bull', 'bear', 'long', 'short', null
    price        REAL,
    confidence   REAL,            -- 0.0 to 1.0 confidence score
    conditions_met TEXT NOT NULL, -- JSON array of conditions that triggered
    market_data  TEXT,            -- JSON snapshot of relevant market data
    timestamp    TEXT NOT NULL,   -- ISO8601
    trade_id     INTEGER,         -- Link to sim_trades if action taken
    outcome      TEXT,            -- 'success', 'failure', 'pending', null
    outcome_price REAL,
    outcome_time TEXT,
    notes        TEXT,            -- Additional notes or LLM analysis
    FOREIGN KEY (strategy_id) REFERENCES strategies(id),
    FOREIGN KEY (trade_id) REFERENCES sim_trades(id)
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
        await get_db.conn.execute(CREATE_STRATEGY_TRIGGERS_TABLE)
    return get_db.conn

async def log_event(event_type: str, payload: dict):
    conn = await get_db()
    await conn.execute(
        "INSERT INTO events (ts, event_type, payload) VALUES (datetime('now'), ?, ?)",
        (event_type, json.dumps(payload)),
    )

async def log_strategy_trigger(
    strategy_id: int,
    strategy_name: str,
    strategy_type: str,
    symbol: str,
    timeframe: str,
    trigger_type: str,
    side: str = None,
    price: float = None,
    confidence: float = None,
    conditions_met: list = None,
    market_data: dict = None,
    trade_id: int = None,
    notes: str = None
):
    """Log a strategy trigger event."""
    conn = await get_db()
    await conn.execute("""
        INSERT INTO strategy_triggers (
            strategy_id, strategy_name, strategy_type, symbol, timeframe,
            trigger_type, side, price, confidence, conditions_met,
            market_data, timestamp, trade_id, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)
    """, (
        strategy_id, strategy_name, strategy_type, symbol, timeframe,
        trigger_type, side, price, confidence, json.dumps(conditions_met or []),
        json.dumps(market_data or {}), trade_id, notes
    ))

async def get_strategy_triggers(
    strategy_id: int = None,
    strategy_name: str = None,
    strategy_type: str = None,
    symbol: str = None,
    timeframe: str = None,
    trigger_type: str = None,
    side: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100
):
    """Get strategy triggers with optional filters."""
    conn = await get_db()
    
    query = "SELECT * FROM strategy_triggers WHERE 1=1"
    params = []
    
    if strategy_id:
        query += " AND strategy_id = ?"
        params.append(strategy_id)
    
    if strategy_name:
        query += " AND strategy_name LIKE ?"
        params.append(f"%{strategy_name}%")
    
    if strategy_type:
        query += " AND strategy_type = ?"
        params.append(strategy_type)
    
    if symbol:
        query += " AND symbol = ?"
        params.append(symbol)
    
    if timeframe:
        query += " AND timeframe = ?"
        params.append(timeframe)
    
    if trigger_type:
        query += " AND trigger_type = ?"
        params.append(trigger_type)
    
    if side:
        query += " AND side = ?"
        params.append(side)
    
    if start_date:
        query += " AND timestamp >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND timestamp <= ?"
        params.append(end_date)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    cursor = await conn.execute(query, params)
    rows = await cursor.fetchall()
    
    # Convert to list of dicts
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in rows]

async def update_trigger_outcome(
    trigger_id: int,
    outcome: str,
    outcome_price: float = None,
    outcome_time: str = None
):
    """Update the outcome of a strategy trigger."""
    conn = await get_db()
    await conn.execute("""
        UPDATE strategy_triggers 
        SET outcome = ?, outcome_price = ?, outcome_time = ?
        WHERE id = ?
    """, (outcome, outcome_price, outcome_time or "datetime('now')", trigger_id)) 