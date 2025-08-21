#!/usr/bin/env python3
"""
ATR Calculator - Reverse Engineered from Saty's ThinkScript
Calculates ATR levels exactly as they appear in the ThinkScript indicator.
"""

import math
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ATRLevels:
    """Container for all ATR levels."""
    previous_close: float
    atr: float
    timeframe: str
    
    # Trigger levels
    lower_trigger: float
    upper_trigger: float
    
    # Fibonacci levels
    lower_0382: float
    upper_0382: float
    lower_0500: float
    upper_0500: float
    lower_0618: float
    upper_0618: float
    lower_0786: float
    upper_0786: float
    lower_1000: float
    upper_1000: float
    
    # Extension levels
    lower_1236: float
    upper_1236: float
    lower_1618: float
    upper_1618: float
    lower_2000: float
    upper_2000: float
    
    # Meta info
    true_range: float = 0.0
    tr_percent_of_atr: float = 0.0

class ATRCalculator:
    """Calculates ATR levels using the exact logic from Saty's ThinkScript."""
    
    def __init__(self, atr_length: int = 14, trigger_percentage: float = 0.236):
        self.atr_length = atr_length
        self.trigger_percentage = trigger_percentage
        self.price_history: Dict[str, List[float]] = {}
        self.high_history: Dict[str, List[float]] = {}
        self.low_history: Dict[str, List[float]] = {}
        
    def add_price_data(self, timeframe: str, high: float, low: float, close: float):
        """Add price data for ATR calculation."""
        if timeframe not in self.price_history:
            self.price_history[timeframe] = []
            self.high_history[timeframe] = []
            self.low_history[timeframe] = []
        
        # Keep only what we need for ATR calculation
        max_history = self.atr_length + 10  # Buffer for accuracy
        
        self.price_history[timeframe].append(close)
        self.high_history[timeframe].append(high)
        self.low_history[timeframe].append(low)
        
        if len(self.price_history[timeframe]) > max_history:
            self.price_history[timeframe] = self.price_history[timeframe][-max_history:]
            self.high_history[timeframe] = self.high_history[timeframe][-max_history:]
            self.low_history[timeframe] = self.low_history[timeframe][-max_history:]
    
    def calculate_true_range(self, high: float, low: float, prev_close: float) -> float:
        """Calculate True Range: max(H-L, H-PC, PC-L)"""
        return max(
            high - low,
            abs(high - prev_close),
            abs(prev_close - low)
        )
    
    def calculate_atr(self, timeframe: str) -> Optional[float]:
        """Calculate ATR using Wilder's smoothing (like ThinkScript)."""
        if timeframe not in self.price_history:
            return None
            
        prices = self.price_history[timeframe]
        highs = self.high_history[timeframe]
        lows = self.low_history[timeframe]
        
        if len(prices) < self.atr_length + 1:
            return None
        
        # Calculate true ranges
        true_ranges = []
        for i in range(1, len(prices)):
            tr = self.calculate_true_range(highs[i], lows[i], prices[i-1])
            true_ranges.append(tr)
        
        if len(true_ranges) < self.atr_length:
            return None
        
        # Wilder's smoothing (like ThinkScript WildersAverage)
        # First ATR is simple average
        first_atr = sum(true_ranges[:self.atr_length]) / self.atr_length
        
        # Subsequent values use Wilder's smoothing: 
        # ATR = ((previous_ATR * (n-1)) + current_TR) / n
        current_atr = first_atr
        for i in range(self.atr_length, len(true_ranges)):
            current_atr = ((current_atr * (self.atr_length - 1)) + true_ranges[i]) / self.atr_length
        
        return round(current_atr, 2)
    
    def calculate_atr_levels(self, timeframe: str, current_high: float = None, current_low: float = None) -> Optional[ATRLevels]:
        """Calculate all ATR levels for a timeframe using exact ThinkScript logic."""
        if timeframe not in self.price_history:
            return None
            
        prices = self.price_history[timeframe]
        if len(prices) < 2:
            return None
        
        # Get previous close (like ThinkScript: close[1])
        previous_close = prices[-2]  # Previous period close
        
        # Calculate ATR
        atr = self.calculate_atr(timeframe)
        if atr is None:
            return None
        
        # Calculate current true range if we have current high/low
        true_range = 0.0
        tr_percent_of_atr = 0.0
        if current_high is not None and current_low is not None:
            true_range = current_high - current_low
            tr_percent_of_atr = round((true_range / atr) * 100, 0) if atr > 0 else 0
        
        # Calculate all levels using exact ThinkScript formulas
        
        # Trigger levels
        lower_trigger = previous_close - (self.trigger_percentage * atr)
        upper_trigger = previous_close + (self.trigger_percentage * atr)
        
        # Fibonacci levels
        lower_0382 = previous_close - (atr * 0.382)
        upper_0382 = previous_close + (atr * 0.382)
        lower_0500 = previous_close - (atr * 0.5)
        upper_0500 = previous_close + (atr * 0.5)
        lower_0618 = previous_close - (atr * 0.618)
        upper_0618 = previous_close + (atr * 0.618)
        lower_0786 = previous_close - (atr * 0.786)
        upper_0786 = previous_close + (atr * 0.786)
        lower_1000 = previous_close - atr
        upper_1000 = previous_close + atr
        
        # Extension levels (based on 1000 level)
        lower_1236 = lower_1000 - (atr * 0.236)
        upper_1236 = upper_1000 + (atr * 0.236)
        lower_1618 = lower_1000 - (atr * 0.618)
        upper_1618 = upper_1000 + (atr * 0.618)
        lower_2000 = lower_1000 - atr
        upper_2000 = upper_1000 + atr
        
        return ATRLevels(
            previous_close=previous_close,
            atr=atr,
            timeframe=timeframe,
            lower_trigger=round(lower_trigger, 2),
            upper_trigger=round(upper_trigger, 2),
            lower_0382=round(lower_0382, 2),
            upper_0382=round(upper_0382, 2),
            lower_0500=round(lower_0500, 2),
            upper_0500=round(upper_0500, 2),
            lower_0618=round(lower_0618, 2),
            upper_0618=round(upper_0618, 2),
            lower_0786=round(lower_0786, 2),
            upper_0786=round(upper_0786, 2),
            lower_1000=round(lower_1000, 2),
            upper_1000=round(upper_1000, 2),
            lower_1236=round(lower_1236, 2),
            upper_1236=round(upper_1236, 2),
            lower_1618=round(lower_1618, 2),
            upper_1618=round(upper_1618, 2),
            lower_2000=round(lower_2000, 2),
            upper_2000=round(upper_2000, 2),
            true_range=round(true_range, 2),
            tr_percent_of_atr=tr_percent_of_atr
        )
    
    def get_atr_levels_dict(self, levels: ATRLevels) -> Dict[str, float]:
        """Convert ATRLevels to dictionary format for strategy evaluation."""
        return {
            "previous_close": levels.previous_close,
            "atr": levels.atr,
            "timeframe": levels.timeframe,
            "lower_trigger": levels.lower_trigger,
            "upper_trigger": levels.upper_trigger,
            "lower_0382": levels.lower_0382,
            "upper_0382": levels.upper_0382,
            "lower_0500": levels.lower_0500,
            "upper_0500": levels.upper_0500,
            "lower_0618": levels.lower_0618,
            "upper_0618": levels.upper_0618,
            "lower_0786": levels.lower_0786,
            "upper_0786": levels.upper_0786,
            "lower_1000": levels.lower_1000,
            "upper_1000": levels.upper_1000,
            "lower_1236": levels.lower_1236,
            "upper_1236": levels.upper_1236,
            "lower_1618": levels.lower_1618,
            "upper_1618": levels.upper_1618,
            "lower_2000": levels.lower_2000,
            "upper_2000": levels.upper_2000,
            "true_range": levels.true_range,
            "tr_percent_of_atr": levels.tr_percent_of_atr
        }
    
    def evaluate_atr_trigger(self, levels: ATRLevels, current_price: float) -> Dict[str, Any]:
        """Evaluate if current price triggers ATR-based signals."""
        triggers = {
            "bull_trigger": current_price > levels.upper_trigger,
            "bear_trigger": current_price < levels.lower_trigger,
            "bull_0382": current_price > levels.upper_0382,
            "bear_0382": current_price < levels.lower_0382,
            "bull_0618": current_price > levels.upper_0618,
            "bear_0618": current_price < levels.lower_0618,
            "bull_1000": current_price > levels.upper_1000,
            "bear_1000": current_price < levels.lower_1000,
            "any_trigger": False
        }
        
        # Check if any trigger is active
        triggers["any_trigger"] = any([
            triggers["bull_trigger"], triggers["bear_trigger"],
            triggers["bull_0382"], triggers["bear_0382"],
            triggers["bull_0618"], triggers["bear_0618"]
        ])
        
        return triggers


# Simulated price data generator for testing
class SPXPriceSimulator:
    """Generates realistic SPX OHLC data for testing ATR calculations."""
    
    def __init__(self, base_price: float = 4500.0):
        self.base_price = base_price
        self.current_price = base_price
        
    def generate_ohlc_bar(self, volatility: float = 0.01) -> Dict[str, float]:
        """Generate a single OHLC bar."""
        import random
        
        # Random walk with mean reversion
        change_percent = random.gauss(0, volatility)
        price_change = self.current_price * change_percent
        
        new_price = self.current_price + price_change
        
        # Ensure reasonable bounds
        new_price = max(4000, min(5000, new_price))
        
        # Generate OHLC around the new price
        range_size = abs(price_change) + random.uniform(1.0, 5.0)
        
        high = new_price + random.uniform(0, range_size)
        low = new_price - random.uniform(0, range_size)
        open_price = self.current_price
        close = new_price
        
        # Ensure OHLC consistency
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        self.current_price = close
        
        return {
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2)
        }


if __name__ == "__main__":
    # Test the ATR calculator
    print("🧪 Testing ATR Calculator")
    print("=" * 40)
    
    calculator = ATRCalculator()
    simulator = SPXPriceSimulator()
    
    # Generate some historical data
    print("📊 Generating test data...")
    for i in range(30):  # 30 periods of data
        bar = simulator.generate_ohlc_bar()
        calculator.add_price_data("day", bar["high"], bar["low"], bar["close"])
        
        if i == 29:  # Last bar
            print(f"Latest OHLC: O:{bar['open']} H:{bar['high']} L:{bar['low']} C:{bar['close']}")
    
    # Calculate ATR levels
    levels = calculator.calculate_atr_levels("day", bar["high"], bar["low"])
    
    if levels:
        print(f"\n📈 ATR Levels (Day timeframe):")
        print(f"Previous Close: ${levels.previous_close}")
        print(f"ATR: ${levels.atr}")
        print(f"True Range: ${levels.true_range} ({levels.tr_percent_of_atr}% of ATR)")
        print(f"\n🎯 Key Levels:")
        print(f"Bull Trigger: ${levels.upper_trigger}")
        print(f"Bear Trigger: ${levels.lower_trigger}")
        print(f"Bull 0.382: ${levels.upper_0382}")
        print(f"Bear 0.382: ${levels.lower_0382}")
        print(f"Bull 0.618: ${levels.upper_0618}")
        print(f"Bear 0.618: ${levels.lower_0618}")
        print(f"Bull 1.0 ATR: ${levels.upper_1000}")
        print(f"Bear 1.0 ATR: ${levels.lower_1000}")
        
        # Test trigger evaluation
        current_price = bar["close"]
        triggers = calculator.evaluate_atr_trigger(levels, current_price)
        
        print(f"\n🔔 Trigger Analysis (Price: ${current_price}):")
        for trigger_name, triggered in triggers.items():
            if triggered and trigger_name != "any_trigger":
                print(f"   ✅ {trigger_name.replace('_', ' ').title()}")
        
        if not triggers["any_trigger"]:
            print("   ℹ️  No triggers active at current price")
            
    else:
        print("❌ Could not calculate ATR levels (insufficient data)") 