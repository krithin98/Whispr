"""Tests for ATR strategy generation and evaluation using the new engine."""

import asyncio
import importlib
import json
import os
import sys

import pytest

# Allow imports from whispr/backend
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "whispr", "backend"))


async def setup_modules(tmp_path, monkeypatch):
    """Prepare database and reload modules for a clean test environment."""

    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_file))

    import database
    import atr_strategy
    import strategies

    importlib.reload(database)
    importlib.reload(atr_strategy)
    importlib.reload(strategies)

    conn = await database.get_db()

    # Minimal tables required for ATR strategies
    await conn.execute(
        """
        CREATE TABLE indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            indicator_type TEXT,
            config TEXT
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            strategy_expression TEXT NOT NULL,
            prompt_tpl TEXT NOT NULL,
            tags TEXT,
            priority INTEGER,
            strategy_type TEXT,
            indicator_ref TEXT,
            indicator_params TEXT,
            is_active INTEGER DEFAULT 1
        )
        """
    )

    return database, atr_strategy, strategies, conn


def test_generate_adjacent_and_multi_level_strategies(tmp_path, monkeypatch):
    """ATR generator creates both adjacent and multi-level strategies."""

    async def run():
        db, atr_strategy, strategies, conn = await setup_modules(tmp_path, monkeypatch)

        spec = {
            "timeframes": ["1d"],
            "adjacent_rules": {
                "lvl1": {"key": "1", "description": "Level 1", "probability": 0.6, "priority": 1}
            },
            "multi_level_rules": {
                "lvl2": {"key": "2", "description": "Level 2", "probability": 0.7, "priority": 2}
            },
        }
        levels = {"1d": {"1": 10, "2": 20}}

        generator = atr_strategy.ATRStrategyGenerator(specification=spec, atr_levels=levels)
        strategies.atr_strategy_generator = generator
        created = await generator.generate_atr_strategies()
        assert created == 4

        cursor = await conn.execute("SELECT name, strategy_expression, tags FROM strategies")
        rows = await cursor.fetchall()
        assert len(rows) == 4

        tags = [json.loads(r[2]) for r in rows]
        assert any(t[0] == "atr_level" for t in tags)
        assert any(t[0] == "atr_multi" for t in tags)

    asyncio.run(run())


def test_check_strategies_matches_baseline(tmp_path, monkeypatch):
    """check_strategies returns same payloads as a baseline evaluator."""

    async def run():
        db, atr_strategy, strategies, conn = await setup_modules(tmp_path, monkeypatch)

        spec = {
            "timeframes": ["1d"],
            "adjacent_rules": {
                "lvl1": {"key": "1", "description": "Level 1", "probability": 0.6, "priority": 1}
            },
            "multi_level_rules": {
                "lvl2": {"key": "2", "description": "Level 2", "probability": 0.7, "priority": 2}
            },
        }
        levels = {"1d": {"1": 10, "2": 20}}

        generator = atr_strategy.ATRStrategyGenerator(specification=spec, atr_levels=levels)
        strategies.atr_strategy_generator = generator
        await generator.generate_atr_strategies()

        tick = {"price": 25, "symbol": "SPY"}

        async def baseline_check():
            strategies_list = await strategies.load_strategies()
            triggered = []
            for strat in strategies_list:
                if strategies.safe_eval(strat["strategy_expression"], tick):
                    triggered.append(strat)
            return triggered

        baseline = await baseline_check()
        refactored = await strategies.check_strategies(tick)

        def simplify(items):
            return [{"id": s["id"], "name": s["name"], "strategy_expression": s["strategy_expression"]} for s in items]

        assert simplify(baseline) == simplify(refactored)

    asyncio.run(run())

