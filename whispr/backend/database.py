import aiosqlite
import json
import os
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "/app/data/whispr.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # /app/data

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    payload     TEXT
);

CREATE TABLE IF NOT EXISTS rules (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    trigger_expr TEXT NOT NULL,   -- e.g. "value > 105"
    prompt_tpl   TEXT NOT NULL,   -- templated text for the LLM
    is_active    INTEGER DEFAULT 1
);
"""

async def get_db():
    """Return a singleton connection (FastAPI will reuse it)."""
    if not hasattr(get_db, "conn"):
        get_db.conn = await aiosqlite.connect(DB_PATH, isolation_level=None)  # autocommit
        await get_db.conn.executescript(CREATE_SQL)
    return get_db.conn

async def log_event(event_type: str, payload: dict):
    conn = await get_db()
    await conn.execute(
        "INSERT INTO events (ts, event_type, payload) VALUES (datetime('now'), ?, ?)",
        (event_type, json.dumps(payload)),
    )


async def log_strategy_trigger(*args, **kwargs):
    """Placeholder for strategy trigger logging used in tests."""
    # The full implementation lives in the production service. For unit tests we
    # simply ignore calls so strategies can import this function without error.
    return None
