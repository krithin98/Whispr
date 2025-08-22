"""Registry for strategy engines.

Allows strategies to be registered under a string key so they can be
instantiated dynamically elsewhere in the application.
"""

from __future__ import annotations

from typing import Dict, Iterable, Type

from .base import StrategyEngine


class RuleRegistry:
    """Simple registry mapping strategy names to engine classes."""

    def __init__(self) -> None:
        self._strategies: Dict[str, Type[StrategyEngine]] = {}

    def register(self, name: str, engine: Type[StrategyEngine]) -> None:
        """Register ``engine`` under ``name``.

        Raises
        ------
        KeyError
            If a strategy with the same ``name`` already exists.
        """

        if name in self._strategies:
            raise KeyError(f"Strategy '{name}' already registered.")
        self._strategies[name] = engine

    def get(self, name: str) -> Type[StrategyEngine]:
        """Return the engine class registered under ``name``."""

        return self._strategies[name]

    def create(self, name: str, *args, **kwargs) -> StrategyEngine:
        """Instantiate a strategy engine by ``name``."""

        engine_cls = self.get(name)
        return engine_cls(*args, **kwargs)

    def names(self) -> Iterable[str]:
        """Return an iterable of all registered strategy names."""

        return self._strategies.keys()


# Global default registry instance used by the application
rule_registry = RuleRegistry()
