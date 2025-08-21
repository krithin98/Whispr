import aiosqlite
import json
import os
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "./data/whispr.db"))
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
        
        # Create level tracking tables
        await create_level_tracking_tables(get_db.conn)
        
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


# ===============================================
# LEVEL TRACKING DATABASE FUNCTIONS
# ===============================================

async def create_level_tracking_tables(conn):
    """Create all level tracking tables."""
    
    # Read and execute schema
    import os
    schema_path = os.path.join(os.path.dirname(__file__), "level_tracking_schema_fixed.sql")
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    # Split by semicolon and execute each statement
    statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
    
    for statement in statements:
        # Check if statement contains CREATE (might have comments before it)
        if 'CREATE TABLE' in statement.upper() or 'CREATE VIEW' in statement.upper():
            try:
                await conn.execute(statement)
                print(f"✅ Executed: {statement.split()[2] if len(statement.split()) > 2 else 'Unknown'}")
            except Exception as e:
                print(f"❌ Failed to execute statement: {e}")
                print(f"Statement: {statement[:100]}...")


async def log_spx_tick(price: float, high: float, low: float, volume: int = 0, timestamp: str = None):
    """Log an SPX price tick."""
    conn = await get_db()
    
    if timestamp is None:
        from datetime import datetime
        timestamp = datetime.now().isoformat()
    
    session_date = timestamp[:10]  # YYYY-MM-DD
    
    await conn.execute("""
        INSERT OR IGNORE INTO spx_price_ticks 
        (timestamp, price, high, low, volume, session_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, price, high, low, volume, session_date))


async def store_atr_levels(timeframe: str, session_date: str, levels_data: dict):
    """Store calculated ATR levels for a timeframe."""
    conn = await get_db()
    from datetime import datetime
    
    await conn.execute("""
        INSERT OR REPLACE INTO atr_levels (
            timeframe, session_date, calculation_time, previous_close, atr_value,
            lower_trigger, upper_trigger, lower_0382, upper_0382, lower_0500, upper_0500,
            lower_0618, upper_0618, lower_0786, upper_0786, lower_1000, upper_1000,
            lower_1236, upper_1236, lower_1618, upper_1618, lower_2000, upper_2000
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timeframe, session_date, datetime.now().isoformat(),
        levels_data['previous_close'], levels_data['atr_value'],
        levels_data['lower_trigger'], levels_data['upper_trigger'],
        levels_data['lower_0382'], levels_data['upper_0382'],
        levels_data['lower_0500'], levels_data['upper_0500'],
        levels_data['lower_0618'], levels_data['upper_0618'],
        levels_data['lower_0786'], levels_data['upper_0786'],
        levels_data['lower_1000'], levels_data['upper_1000'],
        levels_data['lower_1236'], levels_data['upper_1236'],
        levels_data['lower_1618'], levels_data['upper_1618'],
        levels_data['lower_2000'], levels_data['upper_2000']
    ))


async def log_level_hit(
    timeframe: str, level_name: str, level_value: float, hit_price: float,
    direction: str, fib_ratio: float, previous_close: float, atr_value: float,
    hit_time: str = None, session_date: str = None
) -> int:
    """Log a level hit and return the hit ID."""
    conn = await get_db()
    from datetime import datetime
    
    if hit_time is None:
        hit_time = datetime.now().isoformat()
    if session_date is None:
        session_date = hit_time[:10]
    
    cursor = await conn.execute("""
        INSERT INTO level_hits (
            hit_time, timeframe, level_name, level_value, hit_price,
            direction, fib_ratio, previous_close, atr_value, session_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (hit_time, timeframe, level_name, level_value, hit_price,
          direction, fib_ratio, previous_close, atr_value, session_date))
    
    return cursor.lastrowid


async def start_golden_gate_sequence(
    timeframe: str, direction: str, start_level_hit_id: int,
    start_time: str, start_price: float, session_date: str = None
) -> int:
    """Start tracking a Golden Gate sequence (.382 hit)."""
    conn = await get_db()
    
    if session_date is None:
        session_date = start_time[:10]
    
    cursor = await conn.execute("""
        INSERT INTO golden_gate_sequences (
            timeframe, direction, session_date, start_level_hit_id,
            start_time, start_price, completed
        ) VALUES (?, ?, ?, ?, ?, ?, FALSE)
    """, (timeframe, direction, session_date, start_level_hit_id, start_time, start_price))
    
    return cursor.lastrowid


async def complete_golden_gate_sequence(
    sequence_id: int, complete_level_hit_id: int,
    complete_time: str, complete_price: float
):
    """Complete a Golden Gate sequence (.618 hit)."""
    conn = await get_db()
    from datetime import datetime
    
    # Get start data
    start_result = await conn.execute("""
        SELECT start_time, start_price FROM golden_gate_sequences WHERE id = ?
    """, (sequence_id,))
    start_row = await start_result.fetchone()
    
    if start_row:
        start_time = datetime.fromisoformat(start_row[0])
        complete_time_dt = datetime.fromisoformat(complete_time)
        duration_seconds = int((complete_time_dt - start_time).total_seconds())
        price_movement = abs(complete_price - start_row[1])
        
        await conn.execute("""
            UPDATE golden_gate_sequences 
            SET complete_level_hit_id = ?, complete_time = ?, complete_price = ?,
                completed = TRUE, duration_seconds = ?, price_movement = ?
            WHERE id = ?
        """, (complete_level_hit_id, complete_time, complete_price,
              duration_seconds, price_movement, sequence_id))


async def get_recent_level_hits(hours: int = 24) -> list:
    """Get recent level hits."""
    conn = await get_db()
    
    cursor = await conn.execute("""
        SELECT * FROM recent_level_hits
        WHERE datetime(hit_time) > datetime('now', '-{} hours')
        ORDER BY hit_time DESC
    """.format(hours))
    
    return await cursor.fetchall()


async def get_level_transition_stats(timeframe: str, from_level: str, to_level: str, direction: str) -> dict:
    """Get transition statistics between levels."""
    conn = await get_db()
    
    cursor = await conn.execute("""
        SELECT * FROM level_transition_stats
        WHERE timeframe = ? AND from_level = ? AND to_level = ? AND direction = ?
    """, (timeframe, from_level, to_level, direction))
    
    row = await cursor.fetchone()
    if row:
        return {
            'total_occurrences': row[5],
            'successful_hits': row[6], 
            'success_rate': row[7],
            'avg_time_seconds': row[8],
            'min_time_seconds': row[9],
            'max_time_seconds': row[10]
        }
    return None


async def update_daily_session_summary(session_date: str, **kwargs):
    """Update daily session summary stats."""
    conn = await get_db()
    from datetime import datetime
    
    # Build dynamic update
    if kwargs:
        set_clauses = [f"{key} = ?" for key in kwargs.keys()]
        set_clauses.append("last_updated = ?")
        values = list(kwargs.values()) + [datetime.now().isoformat(), session_date]
        
        await conn.execute(f"""
            INSERT OR REPLACE INTO daily_session_summary 
            (session_date, {', '.join(kwargs.keys())}, last_updated)
            VALUES (?, {', '.join(['?' for _ in kwargs])}, ?)
        """, [session_date] + list(kwargs.values()) + [datetime.now().isoformat()]) 