"""Shared pydantic models used across backend modules."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Rule(BaseModel):
    """A simple rule with a boolean trigger expression."""

    id: Optional[int] = None
    name: str
    trigger_expr: str
    prompt_tpl: str
    is_active: bool = True


class Strategy(BaseModel):
    """A complex strategy composed of multiple indicators or rules."""

    id: Optional[int] = None
    name: str
    logic: str  # textual description or expression
    rules: List[Rule] = []
    is_active: bool = True

