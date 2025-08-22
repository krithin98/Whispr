"""Rule evaluation module for simple expressions.

This module deals with basic boolean expressions that can be evaluated
directly against tick data. More complex multi-indicator logic lives in
``strategies.py``.
"""

from __future__ import annotations

import ast
import operator
from typing import AsyncIterator, Dict, List

from database import get_db
from models import Rule

# ---------------------------------------------------------------------------
# Safe expression evaluation
# ---------------------------------------------------------------------------

SAFE_OPS = {
    ast.Gt: operator.gt,
    ast.Lt: operator.lt,
    ast.GtE: operator.ge,
    ast.LtE: operator.le,
    ast.Eq: operator.eq,
}


def _safe_eval(expr: str, context: Dict[str, float | int]) -> bool:
    """Safely evaluate a very small subset of Python expressions.

    Only simple comparisons are supported, e.g. ``value > 105``. Any failure
    during evaluation results in ``False`` to prevent unexpected behaviour.
    """

    try:
        tree = ast.parse(expr, mode="eval").body  # type: ignore[attr-defined]
        if isinstance(tree, ast.Compare):
            left = _safe_eval(ast.unparse(tree.left), context)
            right = _safe_eval(ast.unparse(tree.comparators[0]), context)
            op = SAFE_OPS[type(tree.ops[0])]
            return op(left, right)  # type: ignore[arg-type]
        return context.get(expr, expr)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

async def load_rules() -> List[Rule]:
    """Load all active rules from the database."""
    conn = await get_db()
    rows = await conn.execute_fetchall(
        "SELECT id, name, trigger_expr, prompt_tpl, is_active FROM rules WHERE is_active=1"
    )
    return [
        Rule(
            id=r[0],
            name=r[1],
            trigger_expr=r[2],
            prompt_tpl=r[3],
            is_active=bool(r[4]),
        )
        for r in rows
    ]


async def check_rules(tick: Dict[str, float | int]) -> AsyncIterator[Rule]:
    """Yield rules that match the provided tick data."""
    for rule in await load_rules():
        if _safe_eval(rule.trigger_expr, tick):
            yield rule


async def add_rule(rule: Rule) -> None:
    """Persist a new rule to the database."""
    conn = await get_db()
    await conn.execute(
        "INSERT INTO rules (name, trigger_expr, prompt_tpl, is_active) VALUES (?, ?, ?, ?)",
        (rule.name, rule.trigger_expr, rule.prompt_tpl, int(rule.is_active)),
    )


async def seed_test_rules() -> None:
    """Add some sample rules to get started."""
    test_rules = [
        Rule(
            name="High price ping",
            trigger_expr="value >= 105",
            prompt_tpl="Price crossed {value}. Any risk-reducing actions?",
        ),
        Rule(
            name="Low price alert",
            trigger_expr="value <= 95",
            prompt_tpl="Price dropped to {value}. Consider buying opportunity?",
        ),
        Rule(
            name="Tick milestone",
            trigger_expr="tick % 10 == 0",
            prompt_tpl="Reached tick {tick} with value {value}. Market pattern analysis?",
        ),
    ]

    conn = await get_db()
    for rule in test_rules:
        existing = await conn.execute_fetchall(
            "SELECT id FROM rules WHERE name = ?", (rule.name,)
        )
        if not existing:
            await add_rule(rule)

