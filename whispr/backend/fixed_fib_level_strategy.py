#!/usr/bin/env python3
"""
FIXED Fibonacci Level Strategy
This replaces the broken fib_level_strategy.py with proper timeframe aggregation.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from atr_calculator import ATRCalculator, ATRLevels
from timeframe_aggregator import SPXTimeframeAggregator, ATRCalculatorIntegrator
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
    previous_close: float
    atr_value: float

class FixedFibonacciLevelTracker:
    """
    FIXED Fibonacci level tracker with proper timeframe aggregation.
    This replaces the broken version that treated all timeframes as minute data.
    """
    
    def __init__(self):
        # Core components
        self.atr_calculator = ATRCalculator()
        self.aggregator = SPXTimeframeAggregator()
        self.integrator = ATRCalculatorIntegrator(self.atr_calculator, self.aggregator)
        
        # State tracking
        self.last_levels: Dict[str, Dict[str, ATRLevels]] = {}  # symbol -> timeframe -> levels
        self.last_prices: Dict[str, float] = {}  # symbol -> last price
        self.last_processed_time = datetime.now()
        
        # Fibonacci levels to track (same as before)
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
        
        print("✅ FixedFibonacciLevelTracker initialized with proper aggregation")
    
    async def process_tick(self, symbol: str, price: float, high: float, low: float, 
                          timestamp: datetime = None) -> List[FibLevelHit]:
        """
        FIXED version: Process a new tick with proper timeframe aggregation
        This is the correct implementation that was missing before.
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        hits = []
        
        # Step 1: Add tick data to aggregator (this creates proper timeframe bars)
        self.aggregator.add_tick_data(timestamp, price, high, low)
        
        # Step 2: Update ATR calculator with properly aggregated data
        self.integrator.update_atr_with_aggregated_data()
        
        # Step 3: Check for level hits across all timeframes
        atr_levels_all = self.integrator.get_atr_levels_all_timeframes()
        
        for timeframe_name, level_data in atr_levels_all.items():
            if 'atr_levels' in level_data:
                timeframe_hits = await self._check_timeframe_levels(
                    symbol, timeframe_name, price, level_data['atr_levels'], timestamp
                )
                hits.extend(timeframe_hits)
        
        # Step 4: Update tracking state
        self.last_prices[symbol] = price
        self.last_processed_time = timestamp
        
        # Step 5: Log aggregation info periodically
        if len(hits) > 0:
            await self._log_aggregation_diagnostic()
        
        return hits
    
    async def _check_timeframe_levels(self, symbol: str, timeframe: str, current_price: float, 
                                    atr_levels: ATRLevels, timestamp: datetime) -> List[FibLevelHit]:
        """Check if current price hits any Fibonacci levels for a specific timeframe"""
        hits = []
        
        # Initialize symbol tracking if needed
        if symbol not in self.last_levels:
            self.last_levels[symbol] = {}
        
        # Get previous levels for comparison
        previous_levels = self.last_levels[symbol].get(timeframe)
        
        # Store current levels
        self.last_levels[symbol][timeframe] = atr_levels
        
        # Get previous price for cross detection
        previous_price = self.last_prices.get(symbol, current_price)
        
        # Check each Fibonacci level for hits
        for level_suffix, fib_ratio, description in self.fib_levels:
            
            # Check upper levels (bull direction)
            upper_level_name = f"upper_{level_suffix}"
            if hasattr(atr_levels, upper_level_name):
                upper_level_value = getattr(atr_levels, upper_level_name)
                
                # Detect upward cross (price moves above level)
                if (previous_price <= upper_level_value < current_price):
                    hit = FibLevelHit(
                        symbol=symbol,
                        timeframe=timeframe,
                        level_name=upper_level_name,
                        level_value=upper_level_value,
                        current_price=current_price,
                        hit_time=timestamp,
                        direction="bull",
                        fib_ratio=fib_ratio,
                        previous_close=atr_levels.previous_close,
                        atr_value=atr_levels.atr
                    )
                    hits.append(hit)
                    
                    # Log the hit
                    await self._log_level_hit(hit, description)
            
            # Check lower levels (bear direction)
            lower_level_name = f"lower_{level_suffix}"
            if hasattr(atr_levels, lower_level_name):
                lower_level_value = getattr(atr_levels, lower_level_name)
                
                # Detect downward cross (price moves below level)
                if (previous_price >= lower_level_value > current_price):
                    hit = FibLevelHit(
                        symbol=symbol,
                        timeframe=timeframe,
                        level_name=lower_level_name,
                        level_value=lower_level_value,
                        current_price=current_price,
                        hit_time=timestamp,
                        direction="bear",
                        fib_ratio=fib_ratio,
                        previous_close=atr_levels.previous_close,
                        atr_value=atr_levels.atr
                    )
                    hits.append(hit)
                    
                    # Log the hit
                    await self._log_level_hit(hit, description)
        
        return hits
    
    async def _log_level_hit(self, hit: FibLevelHit, description: str):
        """Log a Fibonacci level hit to database and console"""
        
        # Console log with emoji indicators
        direction_emoji = "🟢" if hit.direction == "bull" else "🔴"
        timeframe_upper = hit.timeframe.upper()
        
        # Special handling for Golden Gate levels
        if "0382" in hit.level_name:
            description += " 🚪 (Golden Gate Entry)"
        elif "0618" in hit.level_name:
            description += " ⭐ (Golden Gate Complete)"
        
        print(f"{direction_emoji} {hit.symbol} {timeframe_upper}: {description}")
        print(f"    Level: ${hit.level_value:.2f} | Price: ${hit.current_price:.2f} | ATR: ${hit.atr_value:.2f}")
        
        # Database log
        await log_event("fibonacci_level_hit", {
            "symbol": hit.symbol,
            "timeframe": hit.timeframe,
            "level_name": hit.level_name,
            "level_value": hit.level_value,
            "current_price": hit.current_price,
            "direction": hit.direction,
            "fib_ratio": hit.fib_ratio,
            "description": description,
            "previous_close": hit.previous_close,
            "atr_value": hit.atr_value,
            "hit_time": hit.hit_time.isoformat()
        })
    
    async def _log_aggregation_diagnostic(self):
        """Log diagnostic info about aggregation state"""
        info = self.aggregator.get_aggregation_info()
        
        await log_event("aggregation_diagnostic", {
            "minute_bars_in_buffer": info["minute_bars_in_buffer"],
            "buffer_time_span_hours": info["buffer_time_span_hours"],
            "timeframe_bar_counts": info["timeframe_bar_counts"],
            "latest_timestamps": info["latest_timestamps"]
        })
    
    def get_current_levels_all_timeframes(self, symbol: str) -> Dict[str, Dict[str, float]]:
        """Get current ATR levels for all timeframes"""
        if symbol not in self.last_levels:
            return {}
        
        result = {}
        for timeframe, atr_levels in self.last_levels[symbol].items():
            if atr_levels:
                result[timeframe] = self.atr_calculator.get_atr_levels_dict(atr_levels)
        
        return result
    
    def get_current_level_proximity(self, symbol: str, current_price: float) -> Dict[str, Dict[str, float]]:
        """Get how close current price is to each level on each timeframe"""
        levels = self.get_current_levels_all_timeframes(symbol)
        proximity = {}
        
        for timeframe, timeframe_levels in levels.items():
            proximity[timeframe] = {}
            
            for level_name, level_value in timeframe_levels.items():
                if isinstance(level_value, (int, float)) and "trigger" in level_name or level_name.startswith(("upper_", "lower_")):
                    distance = abs(current_price - level_value)
                    distance_percent = (distance / level_value) * 100 if level_value != 0 else 0
                    proximity[timeframe][level_name] = {
                        "level_value": level_value,
                        "distance": distance,
                        "distance_percent": distance_percent
                    }
        
        return proximity


# Fibonacci Strategy wrapper (for compatibility with existing system)
class FixedFibonacciStrategy:
    """Wrapper for the fixed fibonacci level tracker"""
    
    def __init__(self):
        self.tracker = FixedFibonacciLevelTracker()
    
    async def evaluate(self, tick_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate fibonacci strategy (compatible with existing system)
        """
        symbol = tick_data.get("symbol", "SPX")
        price = tick_data.get("price", tick_data.get("value", 0))
        high = tick_data.get("high", price)
        low = tick_data.get("low", price)
        
        # Process the tick
        hits = await self.tracker.process_tick(symbol, price, high, low)
        
        # Return result in expected format
        return {
            "triggered": len(hits) > 0,
            "level_hits": [asdict(hit) for hit in hits],
            "hit_count": len(hits),
            "timeframes_with_hits": list(set(hit.timeframe for hit in hits)),
            "current_levels": self.tracker.get_current_levels_all_timeframes(symbol),
            "level_proximity": self.tracker.get_current_level_proximity(symbol, price)
        }


# Global instance (for compatibility)
fixed_fibonacci_strategy = FixedFibonacciStrategy()


if __name__ == "__main__":
    # Test the fixed fibonacci strategy
    print("🧪 Testing Fixed Fibonacci Level Strategy")
    print("=" * 60)
    
    async def test_fixed_strategy():
        tracker = FixedFibonacciLevelTracker()
        
        # Simulate realistic SPX data
        base_price = 5900.0
        
        print("📊 Processing simulated SPX ticks...")
        for i in range(50):
            # Random price movement
            import random
            price_change = random.gauss(0, 1.5)
            base_price += price_change
            
            high = base_price + random.uniform(0, 2.0)
            low = base_price - random.uniform(0, 2.0)
            
            # Process tick
            hits = await tracker.process_tick("SPX", base_price, high, low)
            
            if hits:
                print(f"  🎯 Price: ${base_price:.2f} - {len(hits)} level hits detected")
        
        # Show current state
        print("\n📈 Current Levels Summary:")
        levels = tracker.get_current_levels_all_timeframes("SPX")
        for timeframe, timeframe_levels in levels.items():
            if timeframe_levels:
                print(f"  {timeframe:12}: ATR={timeframe_levels.get('atr', 0):.2f}")
        
        print("\n✅ Fixed strategy test completed!")
    
    # Run the test
    asyncio.run(test_fixed_strategy())
