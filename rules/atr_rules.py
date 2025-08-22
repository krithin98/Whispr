from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class Condition:
    """Represents a rule condition."""
    expression: str
    side: str
    level: float


@dataclass
class Action:
    """Represents an action taken when a rule triggers."""
    name: str
    params: Dict[str, Any]


class PriceCrossesLevel(Condition):
    """Condition for price crossing a specific level."""

    def __init__(self, level: float, side: str) -> None:
        expression = f"price >= {level}" if side == "bull" else f"price <= {level}"
        super().__init__(expression=expression, side=side, level=level)


class LogATRTrigger(Action):
    """Simple logging action for ATR rule triggers."""

    def __init__(self, timeframe: str, tag: str, side: str, level: float) -> None:
        super().__init__(
            name="log_atr_trigger",
            params={
                "timeframe": timeframe,
                "tag": tag,
                "side": side,
                "level": level,
            },
        )


def build_adjacent_rules(timeframe: str, tag: str, level_value: float) -> List[Dict[str, Any]]:
    """Build adjacent level ATR rules for a timeframe and tag.

    Returns a list of rule definitions containing condition/action pairs
    for both bullish and bearish sides.
    """
    rules: List[Dict[str, Any]] = []
    for side in ("bull", "bear"):
        level = level_value if side == "bull" else -level_value
        condition = PriceCrossesLevel(level=level, side=side)
        action = LogATRTrigger(timeframe=timeframe, tag=tag, side=side, level=level)
        rules.append(
            {
                "name": f"ATR {timeframe.capitalize()} {tag} {side.capitalize()}",
                "condition": condition,
                "action": action,
                "tags": ["atr_level", timeframe, tag, side],
                "rule_type": "atr_level",
                "side": side,
            }
        )
    return rules


def build_multi_level_rules(timeframe: str, tag: str, level_value: float) -> List[Dict[str, Any]]:
    """Build multi-level (skip level) ATR rules for a timeframe and tag."""
    rules: List[Dict[str, Any]] = []
    for side in ("bull", "bear"):
        level = level_value if side == "bull" else -level_value
        condition = PriceCrossesLevel(level=level, side=side)
        action = LogATRTrigger(timeframe=timeframe, tag=tag, side=side, level=level)
        rules.append(
            {
                "name": f"ATR {timeframe.capitalize()} {tag} {side.capitalize()}",
                "condition": condition,
                "action": action,
                "tags": ["atr_multi", timeframe, tag, side],
                "rule_type": "atr_multi",
                "side": side,
            }
        )
    return rules
