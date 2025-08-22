import aiosqlite
import json
import os
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "/app/data/whispr.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # /app/data


async def get_db():
    """Return a singleton connection (FastAPI will reuse it)."""
    if not hasattr(get_db, "conn"):
        get_db.conn = await aiosqlite.connect(DB_PATH, isolation_level=None)  # autocommit
    return get_db.conn


async def log_event(event_type: str, payload: dict):
    conn = await get_db()
    await conn.execute(
        "INSERT INTO events (ts, event_type, payload) VALUES (datetime('now'), ?, ?)",
        (event_type, json.dumps(payload)),
    )
