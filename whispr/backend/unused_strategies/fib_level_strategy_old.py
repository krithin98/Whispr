#!/usr/bin/env python3
"""
Fibonacci Level Tracking Strategy
Tracks when price hits specific Fibonacci levels on each timeframe
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from atr_calculator import ATRCalculator, ATRLevels
from database import get_db, log_event

@dataclass
class FibLevelHit:
    """Represents a Fibonacci level hit event"""
    symbol: str
    timeframe: str
    level_name: str  # e.g., "upper_0382", "lower_0618"
    level_value: float
    current_price: float
    hit_time: datetime
    direction: str  # "bull" or "bear"
    fib_ratio: float  # 0.382, 0.618, etc.
    atr_value: float
    previous_close: float

class FibonacciLevelTracker:
    """Tracks Fibonacci level hits across all timeframes"""
    
    def __init__(self):
        self.atr_calculator = ATRCalculator()
        self.last_levels: Dict[str, Dict[str, ATRLevels]] = {}  # symbol -> timeframe -> levels
        self.last_prices: Dict[str, float] = {}  # symbol -> last price
        
        # Timeframes matching ThinkScript
        self.timeframes = {
            "scalp": "4h",      # 4-hour aggregation
            "day": "1d",        # Daily aggregation  
            "multiday": "1w",   # Weekly aggregation
            "swing": "1M",      # Monthly aggregation
            "position": "3M",   # Quarterly aggregation
            "long_term": "1Y"   # Yearly aggregation
        }
        
        # Fibonacci levels to track
        self.fib_levels = [
            ("0236", 0.236, "Trigger"),
            ("0382", 0.382, "Golden Gate Start"),
            ("0500", 0.500, "Mid-Point"),
            ("0618", 0.618, "Golden Gate Complete"),
            ("0786", 0.786, "Extended"),
            ("1000", 1.000, "Full ATR"),
            ("1236", 1.236, "Extension 1"),
            ("1618", 1.618, "Extension 2"),
            ("2000", 2.000, "Double ATR")
        ]
    
    async def process_tick(self, symbol: str, price: float, high: float, low: float) -> List[FibLevelHit]:
        """Process a new tick and check for Fibonacci level hits"""
        hits = []
        
        # Update price history for all timeframes
        for timeframe in self.timeframes.keys():
            self.atr_calculator.add_price_data(timeframe, high, low, price)
        
        # Check each timeframe for level hits
        for timeframe in self.timeframes.keys():
            timeframe_hits = await self._check_timeframe_levels(symbol, timeframe, price)
            hits.extend(timeframe_hits)
        
        # Update last price
        self.last_prices[symbol] = price
        
        return hits
    
    async def _check_timeframe_levels(self, symbol: str, timeframe: str, current_price: float) -> List[FibLevelHit]:
        """Check if price has hit any Fibonacci levels for a specific timeframe"""
        hits = []
        
        # Calculate current levels
        current_levels = self.atr_calculator.calculate_atr_levels(timeframe)
        if not current_levels:
            return hits
        
        # Get previous levels for comparison
        if symbol not in self.last_levels:
            self.last_levels[symbol] = {}
        
        previous_levels = self.last_levels[symbol].get(timeframe)
        last_price = self.last_prices.get(symbol, current_price)
        
        # Store current levels for next comparison
        self.last_levels[symbol][timeframe] = current_levels
        
        # Skip first run (no previous data to compare)
        if previous_levels is None:
            return hits
        
        # Check each Fibonacci level for crossings
        for level_suffix, fib_ratio, description in self.fib_levels:
            # Check upper (bullish) levels
            upper_level_name = f"upper_{level_suffix}"
            if hasattr(current_levels, upper_level_name):
                level_value = getattr(current_levels, upper_level_name)
                
                # Check if price crossed above this level
                if last_price <= level_value < current_price:
                    hit = FibLevelHit(
                        symbol=symbol,
                        timeframe=timeframe,
                        level_name=upper_level_name,
                        level_value=level_value,
                        current_price=current_price,
                        hit_time=datetime.now(),
                        direction="bull",
                        fib_ratio=fib_ratio,
                        atr_value=current_levels.atr,
                        previous_close=current_levels.previous_close
                    )
                    hits.append(hit)
            
            # Check lower (bearish) levels
            lower_level_name = f"lower_{level_suffix}"
            if hasattr(current_levels, lower_level_name):
                level_value = getattr(current_levels, lower_level_name)
                
                # Check if price crossed below this level
                if last_price >= level_value > current_price:
                    hit = FibLevelHit(
                        symbol=symbol,
                        timeframe=timeframe,
                        level_name=lower_level_name,
                        level_value=level_value,
                        current_price=current_price,
                        hit_time=datetime.now(),
                        direction="bear",
                        fib_ratio=fib_ratio,
                        atr_value=current_levels.atr,
                        previous_close=current_levels.previous_close
                    )
                    hits.append(hit)
        
        return hits
    
    async def log_level_hit(self, hit: FibLevelHit):
        """Log a Fibonacci level hit to the database"""
        await log_event("fib_level_hit", {
            "symbol": hit.symbol,
            "timeframe": hit.timeframe,
            "level_name": hit.level_name,
            "level_value": hit.level_value,
            "current_price": hit.current_price,
            "direction": hit.direction,
            "fib_ratio": hit.fib_ratio,
            "atr_value": hit.atr_value,
            "previous_close": hit.previous_close,
            "description": self._get_level_description(hit.level_name, hit.fib_ratio)
        })
    
    def _get_level_description(self, level_name: str, fib_ratio: float) -> str:
        """Get a human-readable description of the level"""
        descriptions = {
            0.236: "Trigger Level",
            0.382: "Golden Gate Start",
            0.500: "Mid-Point",
            0.618: "Golden Gate Complete",
            0.786: "Extended Target",
            1.000: "Full ATR Move",
            1.236: "Extension 1",
            1.618: "Extension 2",
            2.000: "Double ATR"
        }
        return descriptions.get(fib_ratio, f"{fib_ratio:.3f} Level")
    
    def format_alert(self, hit: FibLevelHit) -> str:
        """Format a level hit as an alert message"""
        direction_emoji = "🟢" if hit.direction == "bull" else "🔴"
        timeframe_upper = hit.timeframe.upper()
        
        # Format percentage with negative sign for bearish levels
        if hit.direction == "bear":
            percentage_str = f"-{hit.fib_ratio:.1%}"
        else:
            percentage_str = f"{hit.fib_ratio:.1%}"
        
        # Special handling for trigger levels (23.6%)
        if hit.fib_ratio == 0.236:
            trigger_type = "CALL TRIGGER" if hit.direction == "bull" else "PUT TRIGGER"
            return f"{direction_emoji} {hit.symbol} {timeframe_upper}: {trigger_type} at ${hit.current_price:,.2f} ({percentage_str} ATR)"
        # Special handling for Golden Gate levels
        elif hit.fib_ratio == 0.382:
            gg_status = "GOLDEN GATE ENTRY" if hit.direction == "bull" else "BEARISH GOLDEN GATE ENTRY"
            return f"{direction_emoji} {hit.symbol} {timeframe_upper}: {gg_status} at ${hit.current_price:,.2f} ({percentage_str} ATR)"
        elif hit.fib_ratio == 0.618:
            gg_status = "GOLDEN GATE COMPLETE" if hit.direction == "bull" else "BEARISH GOLDEN GATE COMPLETE"
            return f"⭐ {hit.symbol} {timeframe_upper}: {gg_status} at ${hit.current_price:,.2f} ({percentage_str} ATR)"
        else:
            level_desc = self._get_level_description(hit.level_name, hit.fib_ratio)
            direction_word = "Bullish" if hit.direction == "bull" else "Bearish"
            return f"{direction_emoji} {hit.symbol} {timeframe_upper}: {direction_word} {level_desc} at ${hit.current_price:,.2f} ({percentage_str} ATR)"

class FibonacciStrategy:
    """Main strategy class for Fibonacci level tracking"""
    
    def __init__(self):
        self.tracker = FibonacciLevelTracker()
        self.active = True
    
    async def evaluate(self, tick_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate the strategy against incoming tick data"""
        if not self.active:
            return {"triggered": False}
        
        symbol = tick_data.get("symbol")
        price = tick_data.get("price")
        high = tick_data.get("high", price)
        low = tick_data.get("low", price)
        
        if not all([symbol, price]):
            return {"triggered": False, "reason": "Missing required data"}
        
        # Process the tick and check for level hits
        hits = await self.tracker.process_tick(symbol, price, high, low)
        
        if not hits:
            return {"triggered": False}
        
        # Log all hits and create alerts
        alerts = []
        for hit in hits:
            await self.tracker.log_level_hit(hit)
            alert = self.tracker.format_alert(hit)
            alerts.append(alert)
            
            print(f"🎯 FIB LEVEL HIT: {alert}")
        
        return {
            "triggered": True,
            "strategy_type": "fibonacci_levels",
            "hits": [asdict(hit) for hit in hits],
            "alerts": alerts,
            "total_hits": len(hits)
        }
    
    async def get_current_levels(self, symbol: str) -> Dict[str, Any]:
        """Get current Fibonacci levels for all timeframes"""
        levels = {}
        
        for timeframe in self.tracker.timeframes.keys():
            timeframe_levels = self.tracker.atr_calculator.calculate_atr_levels(timeframe)
            if timeframe_levels:
                levels[timeframe] = {
                    "previous_close": timeframe_levels.previous_close,
                    "atr": timeframe_levels.atr,
                    "levels": {
                        "upper_0236": timeframe_levels.upper_trigger,
                        "upper_0382": timeframe_levels.upper_0382,
                        "upper_0500": timeframe_levels.upper_0500,
                        "upper_0618": timeframe_levels.upper_0618,
                        "upper_0786": timeframe_levels.upper_0786,
                        "upper_1000": timeframe_levels.upper_1000,
                        "upper_1236": timeframe_levels.upper_1236,
                        "upper_1618": timeframe_levels.upper_1618,
                        "upper_2000": timeframe_levels.upper_2000,
                        "lower_0236": timeframe_levels.lower_trigger,
                        "lower_0382": timeframe_levels.lower_0382,
                        "lower_0500": timeframe_levels.lower_0500,
                        "lower_0618": timeframe_levels.lower_0618,
                        "lower_0786": timeframe_levels.lower_0786,
                        "lower_1000": timeframe_levels.lower_1000,
                        "lower_1236": timeframe_levels.lower_1236,
                        "lower_1618": timeframe_levels.lower_1618,
                        "lower_2000": timeframe_levels.lower_2000
                    }
                }
        
        return levels

# Global strategy instance
fibonacci_strategy = FibonacciStrategy() 