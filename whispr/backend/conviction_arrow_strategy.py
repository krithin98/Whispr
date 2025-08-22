"""
Hourly Conviction Arrow Strategy Implementation
Consumes data from existing Saty Pivot Ribbon Pro indicator.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any
from database import get_db, log_event

class ConvictionArrowStrategy:
    """Monitors and tracks hourly conviction arrow signals from existing Pivot Ribbon indicator."""
    
    def __init__(self):
        self.timeframe = "1h"
        self.strategy_type = "conviction_arrow"
        
    async def generate_conviction_arrow_strategy(self):
        """Generate the hourly conviction arrow strategy."""
        conn = await get_db()
        
        # Check if strategy already exists
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM strategies WHERE strategy_type = ? AND timeframe = ?",
            (self.strategy_type, self.timeframe)
        )
        existing_count = await cursor.fetchone()
        
        if existing_count[0] > 0:
            await log_event("conviction_arrow_strategy_exists", {
                "message": f"Conviction arrow strategy already exists ({existing_count[0]} found)"
            })
            return existing_count[0]
        
        # Create the strategy
        strategy_name = "Hourly Conviction Arrow"
        strategy_expression = "HOURLY_CONVICTION_ARROW"
        description = "Monitor conviction arrows (13 EMA vs 48 EMA crosses) on 1H timeframe"
        tags = json.dumps(["conviction_arrow", "1h", "ema_cross"])
        priority = 7  # High priority for conviction signals
        
        indicator_params = json.dumps({
            "timeframe": self.timeframe,
            "ema_fast": 13,
            "ema_slow": 48,
            "evaluation_days": 3,  # Check result after 2-3 trading days
            "indicator_source": "pivot_ribbon_pro"  # References original ThinkScript
        })
        
        await conn.execute(
            """
            INSERT INTO strategies (
                name, strategy_expression, prompt_tpl, tags, priority,
                strategy_type, indicator_ref, indicator_params
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                strategy_name,
                strategy_expression,
                "New conviction arrow detected on 1H timeframe. Direction: {direction}. Will evaluate outcome in 2-3 trading days.",
                tags,
                priority,
                self.strategy_type,
                "pivot_ribbon",
                indicator_params
            )
        )
        
        # Create table for tracking arrow outcomes if it doesn't exist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conviction_arrow_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER NOT NULL,
                arrow_time DATETIME NOT NULL,
                direction TEXT NOT NULL,
                evaluation_due DATETIME NOT NULL,
                evaluated BOOLEAN DEFAULT 0,
                success BOOLEAN DEFAULT NULL,
                evaluation_notes TEXT,
                FOREIGN KEY (strategy_id) REFERENCES strategies(id)
            )
        """)
        
        await log_event("conviction_arrow_strategy_generated", {
            "message": "Generated hourly conviction arrow strategy",
            "timeframe": self.timeframe
        })
        
        return 1
    
    async def evaluate_conviction_arrow(self, strategy_id: int, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate market data for conviction arrows using data from existing Pivot Ribbon indicator.
        Expects market_data to contain:
        - conviction_arrow: { "new_arrow": bool, "direction": str, "ema_13": float, "ema_48": float, "ema_21": float }
        """
        # Get strategy details
        conn = await get_db()
        cursor = await conn.execute(
            "SELECT id, indicator_params FROM strategies WHERE id = ?",
            (strategy_id,)
        )
        strategy = await cursor.fetchone()
        
        if not strategy:
            return {"triggered": False, "error": "Strategy not found"}
        
        strategy_id, indicator_params_json = strategy
        indicator_params = json.loads(indicator_params_json)
        
        # Check if we have a new conviction arrow from the market data
        arrow_data = market_data.get("conviction_arrow", {})
        if not arrow_data.get("new_arrow"):
            return {"triggered": False}
        
        direction = arrow_data.get("direction")
        if not direction:
            return {"triggered": False, "error": "Invalid arrow data"}
        
        # Get EMA values for entry suggestions
        ema_13 = arrow_data.get("ema_13")
        ema_48 = arrow_data.get("ema_48")
        ema_21 = arrow_data.get("ema_21")
        
        # Calculate evaluation due date (2-3 trading days)
        # Note: This is simplified, in reality you'd want to count actual trading days
        evaluation_due = datetime.now() + timedelta(days=3)
        
        # Log the new arrow and schedule follow-up
        await conn.execute(
            """
            INSERT INTO conviction_arrow_outcomes
            (strategy_id, arrow_time, direction, evaluation_due)
            VALUES (?, datetime('now'), ?, ?)
            """,
            (strategy_id, direction, evaluation_due.isoformat())
        )
        
        # Auto-fail any previous unevaluated opposite arrows
        if direction == "bullish":
            opposite = "bearish"
        else:
            opposite = "bullish"
            
        await conn.execute(
            """
            UPDATE conviction_arrow_outcomes
            SET evaluated = 1, success = 0, evaluation_notes = 'Auto-failed due to opposite arrow'
            WHERE strategy_id = ? AND direction = ? AND evaluated = 0
            """,
            (strategy_id, opposite)
        )
        
        # Generate entry suggestion based on 21 EMA
        entry_suggestion = self._get_entry_suggestion(ema_21, direction, ema_13, ema_48)
        
        # Log the event
        await log_event("conviction_arrow_detected", {
            "strategy_id": strategy_id,
            "direction": direction,
            "evaluation_due": evaluation_due.isoformat(),
            "ema_13": ema_13,
            "ema_48": ema_48,
            "ema_21": ema_21,
            "entry_suggestion": entry_suggestion,
            "message": f"New {direction} conviction arrow detected"
        })
        
        return {
            "triggered": True,
            "direction": direction,
            "evaluation_due": evaluation_due.isoformat(),
            "ema_13": ema_13,
            "ema_48": ema_48,
            "ema_21": ema_21,
            "entry_suggestion": entry_suggestion,
            "message": f"New {direction} conviction arrow detected. Will evaluate outcome by {evaluation_due.strftime('%Y-%m-%d %H:%M')}"
        }
    
    def _get_entry_suggestion(self, ema_21: float, direction: str, ema_13: float, ema_48: float) -> str:
        """Generate entry suggestion based on 21 EMA and arrow direction (from original ThinkScript logic)."""
        cross_value = (ema_13 + ema_48) / 2
        
        if direction == "bullish":
            if cross_value < ema_21:
                return f"Bullish conviction arrow below 21 EMA ({ema_21:.2f}). Watch for pullback to EMA for potential entry."
            else:
                return f"Bullish conviction arrow above 21 EMA ({ema_21:.2f}). Monitor for continuation."
        elif direction == "bearish":
            if cross_value > ema_21:
                return f"Bearish conviction arrow above 21 EMA ({ema_21:.2f}). Watch for bounce to EMA for potential entry."
            else:
                return f"Bearish conviction arrow below 21 EMA ({ema_21:.2f}). Monitor for continuation."
        return "No conviction arrow detected."
    
    async def check_pending_evaluations(self) -> list:
        """Check for conviction arrows that need evaluation."""
        conn = await get_db()
        cursor = await conn.execute(
            """
            SELECT id, strategy_id, arrow_time, direction, evaluation_due
            FROM conviction_arrow_outcomes
            WHERE evaluated = 0 AND evaluation_due <= datetime('now')
            """
        )
        pending = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "strategy_id": row[1],
                "arrow_time": row[2],
                "direction": row[3],
                "evaluation_due": row[4]
            }
            for row in pending
        ]
    
    async def record_arrow_outcome(self, outcome_id: int, success: bool, notes: str = None):
        """Record the outcome of a conviction arrow signal."""
        conn = await get_db()
        await conn.execute(
            """
            UPDATE conviction_arrow_outcomes
            SET evaluated = 1, success = ?, evaluation_notes = ?, 
                evaluation_time = datetime('now')
            WHERE id = ?
            """,
            (1 if success else 0, notes, outcome_id)
        )
        
        # Log the outcome
        await log_event("conviction_arrow_evaluated", {
            "outcome_id": outcome_id,
            "success": success,
            "notes": notes
        })
    
    async def get_arrow_statistics(self) -> Dict[str, Any]:
        """Get statistics about conviction arrow performance."""
        conn = await get_db()
        
        # Get overall stats
        cursor = await conn.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN evaluated = 1 AND success = 1 THEN 1 ELSE 0 END) as successes,
                SUM(CASE WHEN evaluated = 1 AND success = 0 THEN 1 ELSE 0 END) as failures,
                SUM(CASE WHEN evaluated = 0 THEN 1 ELSE 0 END) as pending
            FROM conviction_arrow_outcomes
            """
        )
        stats = await cursor.fetchone()
        
        # Get recent arrows
        cursor = await conn.execute(
            """
            SELECT direction, arrow_time, evaluated, success, evaluation_notes
            FROM conviction_arrow_outcomes
            ORDER BY arrow_time DESC LIMIT 5
            """
        )
        recent = await cursor.fetchall()
        
        return {
            "total_signals": stats[0],
            "successful": stats[1],
            "failed": stats[2],
            "pending_evaluation": stats[3],
            "success_rate": (stats[1] / (stats[1] + stats[2])) if (stats[1] + stats[2]) > 0 else 0,
            "recent_signals": [
                {
                    "direction": row[0],
                    "time": row[1],
                    "evaluated": bool(row[2]),
                    "success": bool(row[3]) if row[2] else None,
                    "notes": row[4]
                }
                for row in recent
            ]
        }

# Global instance
conviction_arrow_strategy = ConvictionArrowStrategy() 
