"""ATR-based strategy generation and evaluation using RuleRegistry."""

import json
from typing import Any, Dict, List

from . import Rule, StrategyEngine, RuleRegistry


class ATRStrategy(StrategyEngine):
    """Generates ATR rules and evaluates them against ticks."""

    def __init__(self) -> None:
        super().__init__()
        self.specification = self._load_specification()
        self.atr_levels = self._load_atr_levels()
        self._build_rules()

    # ------------------------------------------------------------------
    # Configuration loading
    def _load_specification(self) -> Dict[str, Any]:
        """Load ATR rule specification from JSON."""
        paths = [
            "data/atr_rule_specification.json",
            "backend/data/atr_rule_specification.json",
            "whispr/backend/data/atr_rule_specification.json",
        ]
        for path in paths:
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except FileNotFoundError:
                continue
        raise FileNotFoundError(
            "atr_rule_specification.json not found in any expected location"
        )

    def _load_atr_levels(self) -> Dict[str, Any]:
        """Load ATR level configuration from JSON."""
        paths = [
            "data/atr_levels.json",
            "backend/data/atr_levels.json",
            "whispr/backend/data/atr_levels.json",
        ]
        for path in paths:
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except FileNotFoundError:
                continue
        raise FileNotFoundError(
            "atr_levels.json not found in any expected location"
        )

    # ------------------------------------------------------------------
    # Rule construction
    def _build_rules(self) -> None:
        for timeframe in self.specification.get("timeframes", []):
            if timeframe not in self.atr_levels:
                continue
            self._build_adjacent_rules(timeframe)
            self._build_multi_level_rules(timeframe)

    def _build_adjacent_rules(self, timeframe: str) -> None:
        levels = self.atr_levels[timeframe]
        for tag, rule_spec in self.specification.get("adjacent_rules", {}).items():
            key = rule_spec["key"]
            if key not in levels:
                continue
            level_value = levels[key]
            description = rule_spec["description"]
            probability = rule_spec["probability"]
            priority = rule_spec["priority"]

            # Bullish rule
            self._register_rule(
                name=f"ATR {timeframe.capitalize()} {tag} Bull",
                rule_type="atr_level",
                timeframe=timeframe,
                tag=tag,
                side="bull",
                level=level_value,
                description=description,
                probability=probability,
                priority=priority,
                expression_str=f"price >= {level_value}",
            )

            # Bearish rule
            self._register_rule(
                name=f"ATR {timeframe.capitalize()} {tag} Bear",
                rule_type="atr_level",
                timeframe=timeframe,
                tag=tag,
                side="bear",
                level=-level_value,
                description=description,
                probability=probability,
                priority=priority,
                expression_str=f"price <= {-level_value}",
            )

    def _build_multi_level_rules(self, timeframe: str) -> None:
        levels = self.atr_levels[timeframe]
        for tag, rule_spec in self.specification.get("multi_level_rules", {}).items():
            key = rule_spec["key"]
            if key not in levels:
                continue
            level_value = levels[key]
            description = rule_spec["description"]
            probability = rule_spec["probability"]
            priority = rule_spec["priority"]

            # Bullish rule
            self._register_rule(
                name=f"ATR {timeframe.capitalize()} {tag} Bull",
                rule_type="atr_multi",
                timeframe=timeframe,
                tag=tag,
                side="bull",
                level=level_value,
                description=description,
                probability=probability,
                priority=priority,
                expression_str=f"price >= {level_value}",
            )

            # Bearish rule
            self._register_rule(
                name=f"ATR {timeframe.capitalize()} {tag} Bear",
                rule_type="atr_multi",
                timeframe=timeframe,
                tag=tag,
                side="bear",
                level=-level_value,
                description=description,
                probability=probability,
                priority=priority,
                expression_str=f"price <= {-level_value}",
            )

    def _register_rule(
        self,
        name: str,
        rule_type: str,
        timeframe: str,
        tag: str,
        side: str,
        level: float,
        description: str,
        probability: float,
        priority: int,
        expression_str: str,
    ) -> None:
        prompt = f"ATR {tag} {side.title()} rule triggered: {description}"

        def check(tick, *, lvl=level, s=side) -> bool:
            price = tick.get("price", tick.get("value", 0))
            return price >= lvl if s == "bull" else price <= lvl

        metadata = {
            "rule_type": rule_type,
            "timeframe": timeframe,
            "tag": tag,
            "side": side,
            "level": level,
            "probability": probability,
            "priority": priority,
            "expression": expression_str,
        }

        rule = Rule(name=name, check=check, prompt=prompt, tags=[rule_type, timeframe, tag, side], metadata=metadata)
        self.register_rule(rule)

    # ------------------------------------------------------------------
    # Evaluation
    def evaluate(self, tick: Dict[str, Any]) -> List[Dict[str, Any]]:  # type: ignore[override]
        triggered = []
        price = tick.get("price", tick.get("value", 0))
        for rule in super().evaluate(tick):
            md = rule.metadata
            result = {
                "triggered": True,
                "rule_expression": md.get("expression"),
                "timeframe": md.get("timeframe"),
                "rule_type": md.get("rule_type"),
                "tag": md.get("tag"),
                "side": md.get("side"),
                "current_price": price,
                "level": md.get("level"),
                "probability": md.get("probability"),
            }
            triggered.append(
                {
                    "name": rule.name,
                    "prompt_tpl": rule.prompt,
                    "strategy_type": "atr_based",
                    "evaluation_result": result,
                }
            )
        return triggered


# Global instance for convenience
atr_strategy = ATRStrategy()

