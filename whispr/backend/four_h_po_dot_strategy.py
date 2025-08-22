"""
4H PO Dot Strategy Implementation
Consumes data from existing Saty Phase Oscillator indicator.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any
from database import get_db, log_event

class PODotStrategyGenerator:
    """Monitors and tracks 4H PO Dot signals from existing Phase Oscillator indicator."""
    
    def __init__(self):
        self.timeframe = "4h"
        self.symbol = "SPX"
        self.strategy_type = "po_dot"
        
    async def generate_po_dot_strategies(self):
        """Generate 4H PO Dot strategies for SPX."""
        conn = await get_db()
        
        # Check if strategies already exist
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM strategies WHERE strategy_type = ? AND indicator_ref = ?",
            (self.strategy_type, "phase_oscillator")
        )
        existing_count = await cursor.fetchone()
        
        if existing_count[0] > 0:
            await log_event("po_dot_strategies_exist", {
                "message": f"PO Dot strategies already exist ({existing_count[0]} found)"
            })
            return existing_count[0]
        
        # Generate the 4H PO Dot strategy
        strategy_name = "4H PO Dot Bullish Cross"
        strategy_expression = "4H_PO_DOT_BULLISH_CROSS"
        description = "Bullish cross dot on 4H Phase Oscillator for SPX"
        tags = json.dumps(["po_dot", "4h", "bullish", "spx", "phase_oscillator"])
        priority = 8  # High priority for mean reversion signals
        
        indicator_params = json.dumps({
            "timeframe": self.timeframe,
            "symbol": self.symbol,
            "strategy_type": self.strategy_type,
            "description": description,
            "indicator_source": "saty_phase_oscillator"  # References original ThinkScript
        })
        
        # Create the strategy
        await conn.execute(
            """
            INSERT INTO strategies (name, strategy_expression, prompt_tpl, tags, priority, strategy_type, indicator_ref, indicator_params)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (strategy_name, strategy_expression, 
             f"4H PO Dot Bullish Cross detected for {self.symbol}. Oscillator value: {{oscillator_value}}, Zone: {{zone}}. Monitor for mean reversion over next 2 weeks.",
             tags, priority, self.strategy_type, "phase_oscillator", indicator_params)
        )
        
        await log_event("po_dot_strategies_generated", {
            "message": f"Generated 4H PO Dot strategy for {self.symbol}",
            "timeframe": self.timeframe,
            "symbol": self.symbol
        })
        
        return 1
    
    async def evaluate_po_dot_strategy(self, strategy_id: int, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate 4H PO Dot strategy using data from existing Phase Oscillator indicator.
        Expects market_data to contain:
        - phase_oscillator: { "oscillator_value": float, "new_bullish_cross": bool, "zone": str }
        """
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
        
        # Get Phase Oscillator data from market_data
        po_data = market_data.get("phase_oscillator", {})
        if not po_data:
            return {"triggered": False, "error": "No Phase Oscillator data available"}
        
        oscillator_value = po_data.get("oscillator_value")
        new_bullish_cross = po_data.get("new_bullish_cross", False)
        zone = po_data.get("zone", "unknown")
        
        if oscillator_value is None:
            return {"triggered": False, "error": "Invalid oscillator value"}
        
        # Check for new bullish cross (from original ThinkScript logic)
        if new_bullish_cross:
            # Calculate evaluation due date (2 weeks)
            evaluation_due = datetime.now() + timedelta(weeks=2)
            
            # Log the PO Dot trigger
            await log_event("po_dot_trigger", {
                "strategy_id": strategy_id,
                "strategy_name": strategy_expression,
                "timeframe": self.timeframe,
                "symbol": self.symbol,
                "oscillator_value": oscillator_value,
                "zone": zone,
                "trigger_time": datetime.now().isoformat()
            })
            
            # Schedule follow-up question in 2 weeks
            await self._schedule_followup(strategy_id, oscillator_value, zone)
            
            return {
                "triggered": True,
                "strategy_type": self.strategy_type,
                "timeframe": self.timeframe,
                "symbol": self.symbol,
                "oscillator_value": oscillator_value,
                "zone": zone,
                "message": f"4H PO Dot Bullish Cross detected for {self.symbol}"
            }
        
        return {"triggered": False}
    
    def get_phase_zone(self, oscillator_value: float) -> str:
        """Get the current phase zone based on oscillator value (from original ThinkScript)."""
        if oscillator_value >= 100:
            return "extended_up"
        elif oscillator_value >= 61.8:
            return "distribution"
        elif oscillator_value > 23.6:
            return "mark_up"
        elif oscillator_value >= -23.6:
            return "launch_box"
        elif oscillator_value > -61.8:
            return "mark_down"
        elif oscillator_value > -100:
            return "accumulation"
        else:
            return "extended_down"
    
    async def _schedule_followup(self, strategy_id: int, oscillator_value: float, zone: str):
        """Schedule a follow-up question about mean reversion in 2 weeks."""
        await log_event("po_dot_followup_scheduled", {
            "strategy_id": strategy_id,
            "followup_date": (datetime.now() + timedelta(weeks=2)).isoformat(),
            "oscillator_value": oscillator_value,
            "zone": zone,
            "message": "Schedule: Ask if 4H PO Dot led to mean reversion"
        })
    
    async def get_po_dot_statistics(self) -> Dict[str, Any]:
        """Get statistics about PO Dot strategy performance."""
        conn = await get_db()
        
        # Count total triggers
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_type = 'po_dot_trigger'"
        )
        total_triggers = await cursor.fetchone()
        
        # Get recent triggers
        cursor = await conn.execute(
            "SELECT payload FROM events WHERE event_type = 'po_dot_trigger' ORDER BY ts DESC LIMIT 5"
        )
        recent_triggers = await cursor.fetchall()
        
        return {
            "total_triggers": total_triggers[0] if total_triggers else 0,
            "recent_triggers": [json.loads(trigger[0]) for trigger in recent_triggers]
        }

# Global instance
po_dot_strategy_generator = PODotStrategyGenerator() 
