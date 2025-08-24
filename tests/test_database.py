"""Tests for database initialization."""

import asyncio
import importlib
import os
import sys


# Allow imports from the backend directory
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "whispr", "backend"))


def test_tables_created(tmp_path, monkeypatch):
    """Verify that required tables are created on initialization."""

    async def run():
        db_file = tmp_path / "test.db"
        monkeypatch.setenv("DB_PATH", str(db_file))

        import database
        importlib.reload(database)

        conn = await database.get_db()
        # Check that both events and rules tables exist
        for table in ("events", "rules"):
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            assert await cursor.fetchone() is not None

    asyncio.run(run())

