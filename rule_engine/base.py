"""Base abstractions for rule driven strategies.

These helpers define minimal interfaces that enable custom strategies to be
registered and executed by the engine.  Concrete implementations should
override the abstract methods with domain specific logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Any


class Condition(ABC):
    """Logical predicate evaluated against a context."""

    @abstractmethod
    def evaluate(self, context: Mapping[str, Any]) -> bool:
        """Return ``True`` when the condition is satisfied.

        Parameters
        ----------
        context:
            Arbitrary data describing the current market state.
        """


class Action(ABC):
    """Executable unit triggered when a rule fires."""

    @abstractmethod
    def execute(self, context: Mapping[str, Any]) -> None:
        """Perform side effects based on ``context``.

        Implementations may place orders, log information or update
        application state.  The engine does not inspect the result.
        """


@dataclass
class Rule:
    """Pair of a condition and the action to execute when it holds."""

    condition: Condition
    action: Action

    def apply(self, context: Mapping[str, Any]) -> None:
        """Evaluate ``condition`` and invoke ``action`` if it is met."""

        if self.condition.evaluate(context):
            self.action.execute(context)


class StrategyEngine:
    """Evaluate incoming market data against registered rules."""

    def __init__(self) -> None:
        self.rules: List[Rule] = []

    def load_rules(self, rules: Iterable[Rule]) -> None:
        """Add rules to the engine."""

        self.rules.extend(rules)

    def run(self, context: Mapping[str, Any]) -> None:
        """Process ``context`` against loaded rules and dispatch actions."""

        for rule in self.rules:
            if rule.condition.evaluate(context):
                rule.action.execute(context)
