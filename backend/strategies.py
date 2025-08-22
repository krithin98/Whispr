"""Strategy evaluation module for complex multi-indicator logic."""

from __future__ import annotations

from typing import AsyncIterator, Dict, List

from models import Strategy
from rules import _safe_eval


async def load_strategies() -> List[Strategy]:
    """Load active strategies.

    For now this function returns an empty list, but it can be extended to
    pull strategies from a database or configuration file.
    """

    return []


async def check_strategies(tick: Dict[str, float | int]) -> AsyncIterator[Strategy]:
    """Yield strategies whose logic evaluates to True for the given tick."""

    for strat in await load_strategies():
        if _safe_eval(strat.logic, tick):
            yield strat

