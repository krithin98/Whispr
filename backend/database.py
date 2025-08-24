import aiosqlite
import json
import os
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "./data/whispr.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

CREATE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    payload     TEXT
)
"""

CREATE_RULES_TABLE = """
CREATE TABLE IF NOT EXISTS rules (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    trigger_expr TEXT NOT NULL,
    prompt_tpl   TEXT NOT NULL,
    is_active    INTEGER DEFAULT 1
)
"""

async def get_db():
    """Return a singleton connection (FastAPI will reuse it)."""
    if not hasattr(get_db, "conn"):
        get_db.conn = await aiosqlite.connect(DB_PATH, isolation_level=None)
        # Execute each CREATE TABLE statement separately
        await get_db.conn.execute(CREATE_EVENTS_TABLE)
        await get_db.conn.execute(CREATE_RULES_TABLE)
    return get_db.conn

async def log_event(event_type: str, payload: dict) -> None:
    conn = await get_db()
    await conn.execute(
        "INSERT INTO events (ts, event_type, payload) VALUES (datetime('now'), ?, ?)",
        (event_type, json.dumps(payload)),
    ) 
