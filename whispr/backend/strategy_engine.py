from typing import Optional

from atr_strategy import ATRStrategyGenerator

class RuleRegistry:
    """Registry for different strategy generators."""

    def __init__(self):
        self._generators = {}

    def register(self, key: str, generator):
        """Register a generator for a strategy type."""
        self._generators[key] = generator

    def get(self, key: str):
        """Retrieve a registered generator."""
        return self._generators.get(key)


class StrategyEngine:
    """Entry point for evaluating strategies via registered generators."""

    def __init__(self, registry: Optional[RuleRegistry] = None):
        self.registry = registry or RuleRegistry()

    async def evaluate_atr_strategy(self, strategy_id: int, price: float, symbol: str):
        """Delegate ATR strategy evaluation to the ATR generator."""
        generator = self.registry.get("atr")
        if not generator:
            raise ValueError("ATRStrategyGenerator not registered")
        return await generator.evaluate_atr_strategy(strategy_id, price, symbol)

    async def generate_atr_strategies(self):
        """Generate ATR strategies via the registered generator."""
        generator = self.registry.get("atr")
        if not generator:
            raise ValueError("ATRStrategyGenerator not registered")
        return await generator.generate_atr_strategies()

    def get_atr_specification(self):
        """Expose the ATR specification from the generator."""
        generator = self.registry.get("atr")
        if not generator:
            raise ValueError("ATRStrategyGenerator not registered")
        return generator.get_atr_specification()


# Create default registry and engine with ATR strategies registered
rule_registry = RuleRegistry()
rule_registry.register("atr", ATRStrategyGenerator())
strategy_engine = StrategyEngine(rule_registry)
