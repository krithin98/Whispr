from dataclasses import dataclass
from typing import Callable, Dict, Any, List, Iterable

@dataclass
class Rule:
    """Simple representation of a trading rule."""
    name: str
    check: Callable[[Dict[str, Any]], bool]
    prompt: str
    tags: List[str]
    metadata: Dict[str, Any]

    def evaluate(self, tick: Dict[str, Any]) -> bool:
        try:
            return self.check(tick)
        except Exception:
            return False

class RuleRegistry:
    """Registry storing all generated rules."""
    _rules: List[Rule] = []

    @classmethod
    def register(cls, rule: Rule) -> None:
        cls._rules.append(rule)

    @classmethod
    def all(cls) -> Iterable[Rule]:
        return list(cls._rules)

class StrategyEngine:
    """Base class for strategy generators."""
    def __init__(self) -> None:
        self.rules: List[Rule] = []

    def register_rule(self, rule: Rule) -> None:
        self.rules.append(rule)
        RuleRegistry.register(rule)

    def evaluate(self, tick: Dict[str, Any]) -> List[Rule]:
        return [rule for rule in self.rules if rule.evaluate(tick)]
