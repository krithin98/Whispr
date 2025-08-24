"""Unit tests for the backtesting engine."""

import asyncio
import importlib
import os
import sys


# Add the backend directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))


def test_backtesting_engine_end_to_end(tmp_path, monkeypatch):
    """Ensure the backtesting engine runs against a seeded database."""

    async def run():
        # Point the database module at a temporary file
        db_file = tmp_path / "test.db"
        monkeypatch.setenv("DB_PATH", str(db_file))

        import database
        importlib.reload(database)

        conn = await database.get_db()
        await conn.executescript(
            """
            CREATE TABLE strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                strategy_expression TEXT NOT NULL,
                strategy_type TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            );
            INSERT INTO strategies (name, strategy_expression, strategy_type)
            VALUES ('Test Strategy', 'dummy_expression', 'atr_based');
            """
        )

        import backtesting
        importlib.reload(backtesting)

        # Basic historical data retrieval
        data = await backtesting.backtesting_engine.get_historical_data(
            symbol="SPY",
            start_date="2024-01-01",
            end_date="2024-01-10",
        )
        assert not data.empty

        # Single strategy backtest
        result = await backtesting.backtesting_engine.backtest_strategy(
            strategy_id=1,
            symbol="SPY",
            start_date="2024-01-01",
            end_date="2024-01-10",
        )
        assert result.strategy_name == "Test Strategy"
        assert result.total_trades >= 0

        # Multiple strategy backtest
        results = await backtesting.backtesting_engine.backtest_multiple_strategies(
            [1], "SPY", "2024-01-01", "2024-01-10"
        )
        assert len(results) == 1

    asyncio.run(run())

