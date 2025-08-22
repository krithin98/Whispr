import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import os
import sys
from database import get_db, log_event

# Ensure root path for importing rule helpers
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from rules.atr_rules import build_adjacent_rules, build_multi_level_rules

class ATRStrategyGenerator:
    """Generates and manages ATR-based rules (adjacent and multi-level)."""
    
    def __init__(self):
        self.specification = self._load_specification()
        self.atr_levels = self._load_atr_levels()
    
    def _load_specification(self) -> Dict[str, Any]:
        """Load the ATR rule specification."""
        try:
            with open("data/atr_rule_specification.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            # Try alternative paths for different service contexts
            try:
                with open("backend/data/atr_rule_specification.json", "r") as f:
                    return json.load(f)
            except FileNotFoundError:
                try:
                    with open("whispr/backend/data/atr_rule_specification.json", "r") as f:
                        return json.load(f)
                except FileNotFoundError:
                    raise FileNotFoundError("atr_rule_specification.json not found in any expected location")
    
    def _load_atr_levels(self) -> Dict[str, Any]:
        """Load ATR levels configuration."""
        try:
            with open("data/atr_levels.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            # Try alternative paths for different service contexts
            try:
                with open("backend/data/atr_levels.json", "r") as f:
                    return json.load(f)
            except FileNotFoundError:
                try:
                    with open("whispr/backend/data/atr_levels.json", "r") as f:
                        return json.load(f)
                except FileNotFoundError:
                    raise FileNotFoundError("atr_levels.json not found in any expected location")
    
    async def generate_atr_strategies(self):
        """Generate all ATR rules for all timeframes."""
        conn = await get_db()
        
        # First, register the ATR levels indicator if not exists
        await self._register_atr_indicator()
        
        total_strategies = 0
        
        # Generate rules for each timeframe
        for timeframe in self.specification["timeframes"]:
            if timeframe not in self.atr_levels:
                await log_event("warning", {"message": f"Timeframe {timeframe} not found in atr_levels.json"})
                continue
            
            # Generate adjacent rules
            adjacent_count = await self._generate_adjacent_rules(timeframe)
            
            # Generate multi-level rules  
            multi_level_count = await self._generate_multi_level_rules(timeframe)
            
            total_strategies += adjacent_count + multi_level_count
            
            await log_event("atr_strategies_generated", {
                "timeframe": timeframe,
                "adjacent_strategies": adjacent_count,
                "multi_level_strategies": multi_level_count
            })
        
        await log_event("atr_strategies_complete", {
            "message": f"Generated {total_strategies} ATR strategies across all timeframes",
            "total_strategies": total_strategies
        })
        
        return total_strategies
    
    async def _register_atr_indicator(self):
        """Register the ATR levels indicator."""
        conn = await get_db()
        await conn.execute(
            "INSERT OR REPLACE INTO indicators (name, indicator_type, config) VALUES (?, ?, ?)",
            ("atr_levels", "atr_levels", json.dumps({
                "atr_length": 14,
                "use_current_close": False
            }))
        )
    
    async def _generate_adjacent_rules(self, timeframe: str) -> int:
        """Generate adjacent (one-step) ATR rules for a timeframe."""
        conn = await get_db()
        strategies_created = 0

        for tag, rule_spec in self.specification["adjacent_rules"].items():
            key = rule_spec["key"]

            if key not in self.atr_levels[timeframe]:
                await log_event("warning", {"message": f"ATR level {key} not found for timeframe {timeframe}"})
                continue

            level_value = self.atr_levels[timeframe][key]

            for rule in build_adjacent_rules(timeframe, tag, level_value):
                await self._create_atr_strategy(
                    rule["name"],
                    rule["condition"].expression,
                    rule_spec["description"],
                    json.dumps(rule["tags"]),
                    rule_spec["probability"],
                    rule_spec["priority"],
                    rule["rule_type"],
                    timeframe,
                    tag,
                    rule["side"],
                    rule["condition"].level,
                    rule["action"].name,
                )
                strategies_created += 1

        return strategies_created
    
    async def _generate_multi_level_rules(self, timeframe: str) -> int:
        """Generate multi-level (skip-a-step) ATR rules for a timeframe."""
        conn = await get_db()
        strategies_created = 0

        for tag, rule_spec in self.specification["multi_level_rules"].items():
            key = rule_spec["key"]

            if key not in self.atr_levels[timeframe]:
                await log_event("warning", {"message": f"ATR level {key} not found for timeframe {timeframe}"})
                continue

            level_value = self.atr_levels[timeframe][key]

            for rule in build_multi_level_rules(timeframe, tag, level_value):
                await self._create_atr_strategy(
                    rule["name"],
                    rule["condition"].expression,
                    rule_spec["description"],
                    json.dumps(rule["tags"]),
                    rule_spec["probability"],
                    rule_spec["priority"],
                    rule["rule_type"],
                    timeframe,
                    tag,
                    rule["side"],
                    rule["condition"].level,
                    rule["action"].name,
                )
                strategies_created += 1

        return strategies_created
    
    async def _create_atr_strategy(self, name: str, expression: str, description: str,
                              tags: str, probability: float, priority: int,
                              rule_type: str, timeframe: str, tag: str, side: str,
                              level: float, action_name: str):
        """Create a single ATR rule."""
        conn = await get_db()
        
        # Check if rule already exists
        cursor = await conn.execute("SELECT id FROM strategies WHERE name = ?", (name,))
        existing = await cursor.fetchone()
        if existing:
            return  # Rule already exists
        
        # Create the rule
        prompt_template = f"ATR {tag} {side.title()} rule triggered: {description}"
        indicator_params = json.dumps({
            "indicator": "atr_levels",
            "timeframe": timeframe,
            "rule_type": rule_type,
            "tag": tag,
            "side": side,
            "level": level,
            "probability": probability,
            "action": action_name,
        })
        
        await conn.execute(
            """
            INSERT INTO strategies (name, rule_expression, prompt_tpl, tags, priority, rule_type, indicator_ref, indicator_params)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, expression, prompt_template, tags, priority, "atr_based", "atr_levels", indicator_params)
        )
    
    async def evaluate_atr_strategy(self, strategy_id: int, current_price: float, symbol: str) -> Dict[str, Any]:
        """Evaluate an ATR rule against current market data."""
        conn = await get_db()
        
        # Get rule details
        cursor = await conn.execute(
            "SELECT rule_expression, indicator_params FROM strategies WHERE id = ?",
            (strategy_id,)
        )
        rule = await cursor.fetchone()
        if not rule:
            return {"triggered": False, "error": "Rule not found"}
        
        rule_expression, indicator_params_json = rule
        indicator_params = json.loads(indicator_params_json)
        
        # Evaluate the rule
        try:
            # Simple evaluation - in production you'd use the safe_eval function
            # For now, we'll do a basic check
            level = indicator_params.get("level", 0)
            side = indicator_params.get("side", "bull")
            
            if side == "bull":
                triggered = current_price >= level
            else:  # bear
                triggered = current_price <= level
            
            if triggered:
                # Log the ATR rule trigger
                await log_event("atr_strategy_trigger", {
                    "strategy_id": strategy_id,
                    "rule_expression": rule_expression,
                    "timeframe": indicator_params.get("timeframe"),
                    "rule_type": indicator_params.get("rule_type"),
                    "tag": indicator_params.get("tag"),
                    "side": side,
                    "price": current_price,
                    "level": level,
                    "symbol": symbol,
                    "probability": indicator_params.get("probability", 0.5)
                })
            
            return {
                "triggered": triggered,
                "rule_expression": rule_expression,
                "timeframe": indicator_params.get("timeframe"),
                "rule_type": indicator_params.get("rule_type"),
                "tag": indicator_params.get("tag"),
                "side": side,
                "current_price": current_price,
                "level": level,
                "probability": indicator_params.get("probability", 0.5)
            }
            
        except Exception as e:
            await log_event("error", {"message": f"ATR rule evaluation failed: {str(e)}"})
            return {"triggered": False, "error": f"Evaluation failed: {str(e)}"}

# Global instance
atr_strategy_generator = ATRStrategyGenerator()
