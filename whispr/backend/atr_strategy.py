import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from database import get_db, log_event

class ATRStrategyGenerator:
    """Generates and manages ATR-based strategies (adjacent and multi-level)."""

    def __init__(self, specification: Dict[str, Any] | None = None,
                 atr_levels: Dict[str, Any] | None = None):
        """Initialize generator with optional injected configuration.

        When specification or ATR levels aren't provided, the generator
        loads them from disk. This flexibility makes unit testing easier
        by allowing tests to supply minimal in-memory configurations.
        """
        self.specification = specification or self._load_specification()
        self.atr_levels = atr_levels or self._load_atr_levels()
    
    def _load_specification(self) -> Dict[str, Any]:
        """Load the ATR strategy specification."""
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
        """Generate all ATR strategys for all timeframes."""
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
        """Generate adjacent (one-step) ATR strategys for a timeframe."""
        conn = await get_db()
        strategies_created = 0
        
        for tag, rule_spec in self.specification["adjacent_rules"].items():
            key = rule_spec["key"]
            
            if key not in self.atr_levels[timeframe]:
                await log_event("warning", {"message": f"ATR level {key} not found for timeframe {timeframe}"})
                continue
            
            level_value = self.atr_levels[timeframe][key]
            
            # Generate bullish rule
            bull_name = f"ATR {timeframe.capitalize()} {tag} Bull"
            bull_expression = f"price >= {level_value}"
            bull_tags = json.dumps(["atr_level", timeframe, tag, "bull"])
            
            await self._create_atr_strategy(
                bull_name, bull_expression, rule_spec["description"], 
                bull_tags, rule_spec["probability"], rule_spec["priority"], 
                "atr_level", timeframe, tag, "bull", level_value
            )
            strategies_created += 1
            
            # Generate bearish rule
            bear_name = f"ATR {timeframe.capitalize()} {tag} Bear"
            bear_expression = f"price <= -{level_value}"
            bear_tags = json.dumps(["atr_level", timeframe, tag, "bear"])
            
            await self._create_atr_strategy(
                bear_name, bear_expression, rule_spec["description"],
                bear_tags, rule_spec["probability"], rule_spec["priority"],
                "atr_level", timeframe, tag, "bear", -level_value
            )
            strategies_created += 1
        
        return strategies_created
    
    async def _generate_multi_level_rules(self, timeframe: str) -> int:
        """Generate multi-level (skip-a-step) ATR strategys for a timeframe."""
        conn = await get_db()
        strategies_created = 0
        
        for tag, rule_spec in self.specification["multi_level_rules"].items():
            key = rule_spec["key"]
            
            if key not in self.atr_levels[timeframe]:
                await log_event("warning", {"message": f"ATR level {key} not found for timeframe {timeframe}"})
                continue
            
            level_value = self.atr_levels[timeframe][key]
            
            # Generate bullish rule
            bull_name = f"ATR {timeframe.capitalize()} {tag} Bull"
            bull_expression = f"price >= {level_value}"
            bull_tags = json.dumps(["atr_multi", timeframe, tag, "bull"])
            
            await self._create_atr_strategy(
                bull_name, bull_expression, rule_spec["description"],
                bull_tags, rule_spec["probability"], rule_spec["priority"],
                "atr_multi", timeframe, tag, "bull", level_value
            )
            strategies_created += 1
            
            # Generate bearish rule
            bear_name = f"ATR {timeframe.capitalize()} {tag} Bear"
            bear_expression = f"price <= -{level_value}"
            bear_tags = json.dumps(["atr_multi", timeframe, tag, "bear"])
            
            await self._create_atr_strategy(
                bear_name, bear_expression, rule_spec["description"],
                bear_tags, rule_spec["probability"], rule_spec["priority"],
                "atr_multi", timeframe, tag, "bear", -level_value
            )
            strategies_created += 1
        
        return strategies_created
    
    async def _create_atr_strategy(
        self,
        name: str,
        expression: str,
        description: str,
        tags: str,
        probability: float,
        priority: int,
        rule_type: str,
        timeframe: str,
        tag: str,
        side: str,
        level: float,
    ) -> None:
        """Create a single ATR strategy."""
        conn = await get_db()

        # Check if strategy already exists
        cursor = await conn.execute("SELECT id FROM strategies WHERE name = ?", (name,))
        existing = await cursor.fetchone()
        if existing:
            return  # Strategy already exists

        prompt_template = f"ATR {tag} {side.title()} rule triggered: {description}"
        indicator_params = json.dumps({
            "indicator": "atr_levels",
            "timeframe": timeframe,
            "rule_type": rule_type,
            "tag": tag,
            "side": side,
            "level": level,
            "probability": probability,
        })

        await conn.execute(
            """
            INSERT INTO strategies (name, strategy_expression, prompt_tpl, tags, priority, strategy_type, indicator_ref, indicator_params)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, expression, prompt_template, tags, priority, "atr_based", "atr_levels", indicator_params),
        )
    
    async def evaluate_atr_strategy(self, strategy_id: int, current_price: float, symbol: str) -> Dict[str, Any]:
        """Evaluate an ATR strategy against current market data."""
        conn = await get_db()
        
        # Get strategy details
        cursor = await conn.execute(
            "SELECT strategy_expression, indicator_params FROM strategies WHERE id = ?",
            (strategy_id,)
        )
        rule = await cursor.fetchone()
        if not rule:
            return {"triggered": False, "error": "Rule not found"}
        
        strategy_expression, indicator_params_json = rule
        indicator_params = json.loads(indicator_params_json)
        
        # Evaluate the strategy
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
                # Log the ATR strategy trigger
                await log_event("atr_strategy_trigger", {
                    "strategy_id": strategy_id,
                    "strategy_expression": strategy_expression,
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
                "strategy_expression": strategy_expression,
                "timeframe": indicator_params.get("timeframe"),
                "rule_type": indicator_params.get("rule_type"),
                "tag": indicator_params.get("tag"),
                "side": side,
                "current_price": current_price,
                "level": level,
                "probability": indicator_params.get("probability", 0.5)
            }
            
        except Exception as e:
            await log_event("error", {"message": f"ATR strategy evaluation failed: {str(e)}"})
            return {"triggered": False, "error": f"Evaluation failed: {str(e)}"}

# Global instance (may be None if config files are missing)
try:
    atr_strategy_generator = ATRStrategyGenerator()
except FileNotFoundError:
    atr_strategy_generator = None
