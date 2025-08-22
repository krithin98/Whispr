import json
import asyncio
from datetime import datetime, time
from typing import Dict, Any, Optional
from database import get_db, log_event

class IndicatorManager:
    """Manages indicator calculations and provides data to strategies."""
    
    def __init__(self):
        self.indicators = {}
        self._load_indicators()
    
    def _load_indicators(self):
        """Load available indicators."""
        self.indicators = {
            "saty_atr_levels": {
                "name": "Saty ATR Levels",
                "type": "atr_levels",
                "description": "ATR-based Fibonacci levels for multiple timeframes",
                "config_schema": {
                    "atr_length": {"type": "int", "default": 14},
                    "trigger_percentage": {"type": "float", "default": 0.236},
                    "use_current_close": {"type": "bool", "default": False}
                }
            }
        }
    
    async def register_indicator(self, name: str, indicator_type: str, config: Dict[str, Any]):
        """Register a new indicator in the database."""
        conn = await get_db()
        await conn.execute(
            "INSERT OR REPLACE INTO indicators (name, indicator_type, config) VALUES (?, ?, ?)",
            (name, indicator_type, json.dumps(config))
        )
        await log_event("indicator_registered", {"name": name, "type": indicator_type})
    
    async def get_indicator_data(self, indicator_name: str, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Get the latest indicator data for a symbol and timeframe."""
        conn = await get_db()
        cursor = await conn.execute(
            """
            SELECT id.data 
            FROM indicator_data id
            JOIN indicators i ON id.indicator_id = i.id
            WHERE i.name = ? AND id.symbol = ? AND id.timeframe = ?
            ORDER BY id.timestamp DESC
            LIMIT 1
            """,
            (indicator_name, symbol, timeframe)
        )
        result = await cursor.fetchone()
        return json.loads(result[0]) if result else None
    
    async def store_indicator_data(self, indicator_name: str, symbol: str, timeframe: str, data: Dict[str, Any]):
        """Store calculated indicator data."""
        conn = await get_db()
        
        # Get indicator ID
        cursor = await conn.execute("SELECT id FROM indicators WHERE name = ?", (indicator_name,))
        indicator_result = await cursor.fetchone()
        if not indicator_result:
            await log_event("error", {"message": f"Indicator {indicator_name} not found"})
            return
        
        indicator_id = indicator_result[0]
        
        # Store the data
        await conn.execute(
            """
            INSERT INTO indicator_data (indicator_id, symbol, timeframe, timestamp, data)
            VALUES (?, ?, ?, datetime('now'), ?)
            """,
            (indicator_id, symbol, timeframe, json.dumps(data))
        )
    
    def calculate_atr_levels(self, previous_close: float, atr: float, config: Dict[str, Any]) -> Dict[str, float]:
        """Calculate ATR levels based on Saty's formula."""
        trigger_percentage = config.get("trigger_percentage", 0.236)
        
        return {
            "previous_close": previous_close,
            "atr": atr,
            "lower_trigger": previous_close - (trigger_percentage * atr),
            "upper_trigger": previous_close + (trigger_percentage * atr),
            "lower_0382": previous_close - (atr * 0.382),
            "upper_0382": previous_close + (atr * 0.382),
            "lower_0500": previous_close - (atr * 0.5),
            "upper_0500": previous_close + (atr * 0.5),
            "lower_0618": previous_close - (atr * 0.618),
            "upper_0618": previous_close + (atr * 0.618),
            "lower_0786": previous_close - (atr * 0.786),
            "upper_0786": previous_close + (atr * 0.786),
            "lower_1000": previous_close - atr,
            "upper_1000": previous_close + atr
        }

class GoldenGateRuleGenerator:
    """Generates and manages Golden Gate strategies based on ATR levels."""
    
    def __init__(self, indicator_manager: IndicatorManager):
        self.indicator_manager = indicator_manager
        self.timeframes = ["scalp", "day", "multiday", "swing", "position", "long_term"]
        self.day_probabilities = self._load_day_probabilities()
    
    def _load_day_probabilities(self) -> Dict[str, Any]:
        """Load Day GG completion probabilities."""
        try:
            with open("data/day_gg_probabilities.json", "r") as f:
                data = json.load(f)
                return data.get("day_gg_probabilities", {})
        except FileNotFoundError:
            return {}
    
    def _get_trigger_time_slot(self, trigger_time: datetime) -> str:
        """Determine the trigger time slot for Day GG probabilities."""
        current_time = trigger_time.time()
        
        # Check for exact open time
        if current_time == time(9, 30, 0):
            return "open"
        
        # Check time ranges
        if time(9, 30, 1) <= current_time <= time(9, 59, 59):
            return "09_00"
        elif time(10, 0, 0) <= current_time <= time(10, 59, 59):
            return "10_00"
        elif time(11, 0, 0) <= current_time <= time(11, 59, 59):
            return "11_00"
        elif time(12, 0, 0) <= current_time <= time(12, 59, 59):
            return "12_00"
        elif time(13, 0, 0) <= current_time <= time(13, 59, 59):
            return "13_00"
        elif time(14, 0, 0) <= current_time <= time(14, 59, 59):
            return "14_00"
        elif time(15, 0, 0) <= current_time <= time(15, 59, 59):
            return "15_00"
        else:
            return "unknown"
    
    def _get_completion_probability(self, timeframe: str, side: str, trigger_time: datetime) -> float:
        """Get the completion probability for a Day GG trigger."""
        if timeframe != "day":
            return 0.5  # Default probability for non-day timeframes
        
        time_slot = self._get_trigger_time_slot(trigger_time)
        side_key = "bullish" if side == "bull" else "bearish"
        
        if side_key in self.day_probabilities and time_slot in self.day_probabilities[side_key]:
            return self.day_probabilities[side_key][time_slot]["completion_rates"]["cumulative_total"]
        
        return 0.5  # Default if no data available
    
    async def generate_golden_gate_strategies(self):
        """Generate all Golden Gate strategies for all timeframes."""
        conn = await get_db()
        
        # First, register the ATR levels indicator if not exists
        await self.indicator_manager.register_indicator(
            "saty_atr_levels",
            "atr_levels",
            {"atr_length": 14, "trigger_percentage": 0.236, "use_current_close": False}
        )
        
        # Load ATR levels configuration
        try:
            with open("data/atr_levels.json", "r") as f:
                atr_levels = json.load(f)
        except FileNotFoundError:
            await log_event("error", {"message": "atr_levels.json not found"})
            return
        
        # Generate strategies for each timeframe
        for timeframe in self.timeframes:
            if timeframe not in atr_levels:
                await log_event("warning", {"message": f"Timeframe {timeframe} not found in atr_levels.json"})
                continue
            
            levels = atr_levels[timeframe]
            
            # Generate Bull strategies
            await self._create_gg_strategy(
                f"GG {timeframe.capitalize()} Bull Trigger",
                "golden_gate",
                timeframe,
                "bull",
                "trigger",
                levels["atr_0382"],
                9
            )
            
            await self._create_gg_strategy(
                f"GG {timeframe.capitalize()} Bull Complete",
                "golden_gate",
                timeframe,
                "bull",
                "complete",
                levels["atr_0618"],
                8
            )
            
            # Generate Bear strategies
            await self._create_gg_strategy(
                f"GG {timeframe.capitalize()} Bear Trigger",
                "golden_gate",
                timeframe,
                "bear",
                "trigger",
                -levels["atr_0382"],
                9
            )
            
            await self._create_gg_strategy(
                f"GG {timeframe.capitalize()} Bear Complete",
                "golden_gate",
                timeframe,
                "bear",
                "complete",
                -levels["atr_0618"],
                8
            )
        
        await log_event("strategies_generated", {"message": f"Generated Golden Gate strategies for {len(self.timeframes)} timeframes"})
    
    async def _create_gg_strategy(self, name: str, strategy_type: str, timeframe: str, side: str, event_type: str, level: float, priority: int):
        """Create a single Golden Gate strategy."""
        conn = await get_db()
        
        # Check if strategy already exists
        cursor = await conn.execute("SELECT id FROM strategies WHERE name = ?", (name,))
        existing = await cursor.fetchone()
        if existing:
            return  # Strategy already exists
        
        # Create the strategy
        strategy_expression = f"GG {timeframe.capitalize()} {side.title()} {event_type.title()}"
        tags = json.dumps(["golden_gate", timeframe, event_type, side])
        indicator_params = json.dumps({
            "indicator": "saty_atr_levels",
            "timeframe": timeframe,
            "side": side,
            "event_type": event_type,
            "level": level
        })
        
        await conn.execute(
            """
            INSERT INTO strategies (name, strategy_expression, prompt_tpl, tags, priority, strategy_type, indicator_ref, indicator_params)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, strategy_expression, f"Golden Gate {event_type} detected for {timeframe} {side} at level {level}", 
             tags, priority, strategy_type, "saty_atr_levels", indicator_params)
        )
    
    async def evaluate_gg_strategy(self, strategy_id: int, current_price: float, symbol: str, current_time: datetime = None) -> Dict[str, Any]:
        """Evaluate a Golden Gate strategy against current market data."""
        if current_time is None:
            current_time = datetime.now()
            
        conn = await get_db()
        
        # Get strategy details
        cursor = await conn.execute(
            "SELECT strategy_expression, indicator_params FROM strategies WHERE id = ?",
            (strategy_id,)
        )
        strategy = await cursor.fetchone()
        if not strategy:
            return {"triggered": False, "error": "Strategy not found"}
        
        strategy_expression, indicator_params_json = strategy
        indicator_params = json.loads(indicator_params_json)
        
        # Get indicator data
        indicator_data = await self.indicator_manager.get_indicator_data(
            indicator_params["indicator"],
            symbol,
            indicator_params["timeframe"]
        )
        
        if not indicator_data:
            return {"triggered": False, "error": "No indicator data available"}
        
        # Evaluate the strategy based on type
        timeframe = indicator_params["timeframe"]
        side = indicator_params["side"]
        event_type = indicator_params["event_type"]
        
        # Get current strategy state
        cursor = await conn.execute(
            """
            SELECT is_active, triggered_at, completed_at FROM strategy_states 
            WHERE strategy_id = ? AND timeframe = ? AND side = ? AND event_type = ?
            """,
            (strategy_id, timeframe, side, event_type)
        )
        state = await cursor.fetchone()
        
        # Determine if strategy should trigger
        triggered = False
        should_log = False
        completion_probability = 0.0
        
        if event_type == "trigger":
            if side == "bull":
                triggered = current_price >= indicator_params["level"]
            else:  # bear
                triggered = current_price <= indicator_params["level"]
            
            # Only trigger if not already active
            if triggered and (not state or not state[0]):
                should_log = True
                completion_probability = self._get_completion_probability(timeframe, side, current_time)
                
                # Activate the trigger state
                if state:
                    await conn.execute(
                        "UPDATE strategy_states SET is_active = 1, triggered_at = datetime('now') WHERE strategy_id = ? AND timeframe = ? AND side = ? AND event_type = ?",
                        (strategy_id, timeframe, side, event_type)
                    )
                else:
                    await conn.execute(
                        "INSERT INTO strategy_states (strategy_id, timeframe, side, event_type, is_active, triggered_at) VALUES (?, ?, ?, ?, 1, datetime('now'))",
                        (strategy_id, timeframe, side, event_type)
                    )
                
                # Log the trigger with probability
                await log_event("golden_gate_trigger", {
                    "strategy_id": strategy_id,
                    "strategy_name": strategy_expression,
                    "timeframe": timeframe,
                    "side": side,
                    "event_type": event_type,
                    "price": current_price,
                    "level": indicator_params["level"],
                    "symbol": symbol,
                    "completion_probability": completion_probability,
                    "trigger_time": current_time.isoformat(),
                    "time_slot": self._get_trigger_time_slot(current_time)
                })
        
        elif event_type == "complete":
            if side == "bull":
                triggered = current_price >= indicator_params["level"]
            else:  # bear
                triggered = current_price <= indicator_params["level"]
            
            # Only complete if trigger is active and not already completed
            if triggered and state and state[0] and not state[1]:  # is_active but not completed
                should_log = True
                
                # Calculate time to completion
                trigger_time = datetime.fromisoformat(state[1]) if state[1] else current_time
                time_to_completion = (current_time - trigger_time).total_seconds() / 3600  # hours
                
                # Mark as completed
                await conn.execute(
                    "UPDATE strategy_states SET is_active = 0, completed_at = datetime('now') WHERE strategy_id = ? AND timeframe = ? AND side = ? AND event_type = ?",
                    (strategy_id, timeframe, side, event_type)
                )
                
                # Log the completion
                await log_event("golden_gate_complete", {
                    "strategy_id": strategy_id,
                    "strategy_name": strategy_expression,
                    "timeframe": timeframe,
                    "side": side,
                    "event_type": event_type,
                    "price": current_price,
                    "level": indicator_params["level"],
                    "symbol": symbol,
                    "time_to_completion_hours": time_to_completion,
                    "completion_time": current_time.isoformat()
                })
        
        # Check for triggered-but-not-completed events (for analysis)
        if event_type == "trigger" and state and state[0] and not state[1]:
            # This is a trigger that's active but not completed
            trigger_time = datetime.fromisoformat(state[1]) if state[1] else current_time
            time_since_trigger = (current_time - trigger_time).total_seconds() / 3600  # hours
            
            # Log if it's been more than 1 hour without completion (for analysis)
            if time_since_trigger >= 1.0:
                await log_event("golden_gate_pending", {
                    "strategy_id": strategy_id,
                    "strategy_name": strategy_expression,
                    "timeframe": timeframe,
                    "side": side,
                    "time_since_trigger_hours": time_since_trigger,
                    "current_price": current_price,
                    "level": indicator_params["level"],
                    "symbol": symbol
                })
        
        return {
            "triggered": triggered,
            "strategy_expression": strategy_expression,
            "timeframe": timeframe,
            "side": side,
            "event_type": event_type,
            "current_price": current_price,
            "level": indicator_params["level"],
            "completion_probability": completion_probability,
            "time_slot": self._get_trigger_time_slot(current_time) if event_type == "trigger" else None
        }

# Global instances
indicator_manager = IndicatorManager()
gg_rule_generator = GoldenGateRuleGenerator(indicator_manager) 
