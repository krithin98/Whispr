import pytest
import sys
import asyncio
from pathlib import Path

# Ensure backend modules are importable when tests are executed from repository root
sys.path.append(str(Path(__file__).resolve().parents[1]))

import rules
from rules import _safe_eval, check_rules

@pytest.mark.parametrize(
    "expr, context, expected",
    [
        ("value >= 105", {"value": 105}, True),
        ("value < 100", {"value": 105}, False),
        ("value => 100", {"value": 101}, False),
    ],
)
def test_safe_eval(expr, context, expected):
    assert _safe_eval(expr, context) is expected

def test_check_rules_triggers(monkeypatch):
    sample_rules = [
        {"id": 1, "name": "High", "expr": "value >= 105", "tpl": "High"},
        {"id": 2, "name": "Low", "expr": "value <= 95", "tpl": "Low"},
    ]

    async def fake_load_rules():
        return sample_rules

    monkeypatch.setattr(rules, "load_rules", fake_load_rules)

    tick_data = {"tick": 5, "value": 105}

    async def collect():
        return [r async for r in check_rules(tick_data)]

    triggered = asyncio.run(collect())
    assert [r["name"] for r in triggered] == ["High"]

def test_check_rules_no_trigger(monkeypatch):
    sample_rules = [
        {"id": 1, "name": "High", "expr": "value >= 105", "tpl": "High"},
    ]

    async def fake_load_rules():
        return sample_rules

    monkeypatch.setattr(rules, "load_rules", fake_load_rules)

    tick_data = {"tick": 1, "value": 100}

    async def collect():
        return [r async for r in check_rules(tick_data)]

    triggered = asyncio.run(collect())
    assert triggered == []
