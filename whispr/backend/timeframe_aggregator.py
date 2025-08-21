#!/usr/bin/env python3
"""
SPX Timeframe Aggregator
Converts 1-minute SPX data into proper timeframe OHLC bars for ATR calculations.
Fixes the core aggregation problem in the current system.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

@dataclass
class OHLCBar:
    """Represents a single OHLC bar"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    timeframe: str

class SPXTimeframeAggregator:
    """
    Handles aggregation of 1-minute SPX data into your 6 timeframes.
    This fixes the current system where all timeframes incorrectly use minute data.
    """
    
    def __init__(self, buffer_size: int = 2000):
        """
        Args:
            buffer_size: How many minute bars to keep in memory (default: ~33 hours)
        """
        self.buffer_size = buffer_size
        self.minute_data_buffer: List[OHLCBar] = []
        
        # Your 6 timeframe mappings to pandas frequency strings (updated for newer pandas)
        self.timeframe_mapping = {
            "scalp": "4h",        # 4-hour aggregation
            "day": "1D",          # Daily aggregation  
            "multiday": "1W",     # Weekly aggregation
            "swing": "1ME",       # Monthly aggregation (Month End)
            "position": "3ME",    # Quarterly aggregation (3 months)
            "long_term": "1YE"    # Yearly aggregation (Year End)
        }
        
        # Cache for aggregated data to avoid recalculation
        self.aggregated_cache: Dict[str, List[OHLCBar]] = {
            tf: [] for tf in self.timeframe_mapping.keys()
        }
        
        self.last_aggregation_time = {}
        
    def add_minute_bar(self, timestamp: datetime, open_price: float, high: float, 
                      low: float, close: float, volume: int = 1000):
        """Add a new minute-level OHLC bar to the buffer"""
        
        minute_bar = OHLCBar(
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            timeframe="1m"
        )
        
        self.minute_data_buffer.append(minute_bar)
        
        # Keep only recent data to prevent memory bloat
        if len(self.minute_data_buffer) > self.buffer_size:
            self.minute_data_buffer = self.minute_data_buffer[-self.buffer_size:]
    
    def add_tick_data(self, timestamp: datetime, price: float, high: float = None, 
                     low: float = None, volume: int = 1000):
        """
        Convert tick data to minute bar (simplified for real-time use)
        In production, you'd accumulate ticks into proper minute bars
        """
        if high is None:
            high = price
        if low is None:
            low = price
            
        # For now, treat each tick as a minute bar (you can improve this)
        self.add_minute_bar(timestamp, price, high, low, price, volume)
    
    def get_aggregated_timeframes(self) -> Dict[str, List[OHLCBar]]:
        """
        Get all timeframes aggregated from current minute data
        Returns: Dict with timeframe names as keys, list of OHLC bars as values
        """
        if len(self.minute_data_buffer) < 10:
            return {tf: [] for tf in self.timeframe_mapping.keys()}
        
        # Convert minute buffer to pandas DataFrame
        df_1min = self._buffer_to_dataframe()
        
        aggregated_data = {}
        
        for timeframe_name, pandas_freq in self.timeframe_mapping.items():
            try:
                # Aggregate using pandas resample
                df_aggregated = self._resample_ohlc(df_1min, pandas_freq)
                
                # Convert back to OHLCBar objects
                bars = self._dataframe_to_bars(df_aggregated, timeframe_name)
                aggregated_data[timeframe_name] = bars
                
            except Exception as e:
                print(f"⚠️  Aggregation error for {timeframe_name}: {e}")
                aggregated_data[timeframe_name] = []
        
        return aggregated_data
    
    def get_latest_bar(self, timeframe: str) -> Optional[OHLCBar]:
        """Get the most recent aggregated bar for a specific timeframe"""
        aggregated = self.get_aggregated_timeframes()
        
        if timeframe in aggregated and aggregated[timeframe]:
            return aggregated[timeframe][-1]
        
        return None
    
    def get_timeframe_history(self, timeframe: str, periods: int = 14) -> List[OHLCBar]:
        """
        Get recent history for a timeframe (useful for ATR calculation)
        Args:
            timeframe: One of your 6 timeframes
            periods: Number of recent bars to return
        """
        aggregated = self.get_aggregated_timeframes()
        
        if timeframe in aggregated and aggregated[timeframe]:
            return aggregated[timeframe][-periods:]
        
        return []
    
    def _buffer_to_dataframe(self) -> pd.DataFrame:
        """Convert minute buffer to pandas DataFrame with proper index"""
        data = {
            'timestamp': [bar.timestamp for bar in self.minute_data_buffer],
            'open': [bar.open for bar in self.minute_data_buffer],
            'high': [bar.high for bar in self.minute_data_buffer],
            'low': [bar.low for bar in self.minute_data_buffer],
            'close': [bar.close for bar in self.minute_data_buffer],
            'volume': [bar.volume for bar in self.minute_data_buffer]
        }
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        df.index = pd.to_datetime(df.index)
        
        return df
    
    def _resample_ohlc(self, df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """
        Standard OHLC aggregation using pandas resample
        This is the proven method used by all trading systems
        """
        agg_rules = {
            'open': 'first',    # First price in the period
            'high': 'max',      # Highest price in the period
            'low': 'min',       # Lowest price in the period
            'close': 'last',    # Last price in the period
            'volume': 'sum'     # Total volume in the period
        }
        
        # Use market-aware resampling (9:30 AM - 4:00 PM ET)
        # For now, we'll use simple resampling - you can add market hours later
        resampled = df.resample(freq, label='right', closed='right').agg(agg_rules)
        
        # Remove any bars with NaN values
        return resampled.dropna()
    
    def _dataframe_to_bars(self, df: pd.DataFrame, timeframe: str) -> List[OHLCBar]:
        """Convert pandas DataFrame back to OHLCBar objects"""
        bars = []
        
        for timestamp, row in df.iterrows():
            bar = OHLCBar(
                timestamp=timestamp,
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume']),
                timeframe=timeframe
            )
            bars.append(bar)
        
        return bars
    
    def get_aggregation_info(self) -> Dict[str, any]:
        """Get diagnostic information about current aggregation state"""
        aggregated = self.get_aggregated_timeframes()
        
        info = {
            "minute_bars_in_buffer": len(self.minute_data_buffer),
            "buffer_time_span_hours": 0,
            "timeframe_bar_counts": {},
            "latest_timestamps": {}
        }
        
        if self.minute_data_buffer:
            time_span = self.minute_data_buffer[-1].timestamp - self.minute_data_buffer[0].timestamp
            info["buffer_time_span_hours"] = time_span.total_seconds() / 3600
        
        for tf_name, bars in aggregated.items():
            info["timeframe_bar_counts"][tf_name] = len(bars)
            if bars:
                info["latest_timestamps"][tf_name] = bars[-1].timestamp.isoformat()
        
        return info


# Integration helper for your existing ATR calculator
class ATRCalculatorIntegrator:
    """
    Helper class to integrate the aggregator with your existing ATR calculator
    """
    
    def __init__(self, atr_calculator, aggregator: SPXTimeframeAggregator):
        self.atr_calculator = atr_calculator
        self.aggregator = aggregator
    
    def update_atr_with_aggregated_data(self):
        """
        Update ATR calculator with properly aggregated timeframe data
        This replaces the broken logic in fib_level_strategy.py
        """
        aggregated_data = self.aggregator.get_aggregated_timeframes()
        
        for timeframe_name, bars in aggregated_data.items():
            if bars:
                # Get the latest bar for this timeframe
                latest_bar = bars[-1]
                
                # Add to ATR calculator (this is the CORRECT way)
                self.atr_calculator.add_price_data(
                    timeframe_name,
                    latest_bar.high,
                    latest_bar.low,
                    latest_bar.close
                )
    
    def get_atr_levels_all_timeframes(self) -> Dict[str, any]:
        """Calculate ATR levels for all timeframes using correct aggregated data"""
        levels = {}
        
        for timeframe_name in self.aggregator.timeframe_mapping.keys():
            latest_bar = self.aggregator.get_latest_bar(timeframe_name)
            
            if latest_bar:
                atr_levels = self.atr_calculator.calculate_atr_levels(
                    timeframe_name,
                    latest_bar.high,
                    latest_bar.low
                )
                
                if atr_levels:
                    levels[timeframe_name] = {
                        'atr_levels': atr_levels,
                        'current_price': latest_bar.close,
                        'bar_timestamp': latest_bar.timestamp.isoformat()
                    }
        
        return levels


if __name__ == "__main__":
    # Test the aggregator
    print("🧪 Testing SPX Timeframe Aggregator")
    print("=" * 50)
    
    aggregator = SPXTimeframeAggregator()
    
    # Simulate some minute data
    import random
    base_price = 5900.0
    current_time = datetime.now()
    
    print("📊 Adding simulated minute data...")
    for i in range(300):  # 5 hours of minute data
        # Random walk
        price_change = random.gauss(0, 2.0)
        base_price += price_change
        
        # Create OHLC for the minute
        high = base_price + random.uniform(0, 1.5)
        low = base_price - random.uniform(0, 1.5)
        volume = random.randint(1000, 5000)
        
        timestamp = current_time + timedelta(minutes=i)
        aggregator.add_minute_bar(timestamp, base_price, high, low, base_price, volume)
    
    # Test aggregation
    print("\n📈 Testing aggregation...")
    aggregated = aggregator.get_aggregated_timeframes()
    
    for timeframe, bars in aggregated.items():
        print(f"{timeframe:12}: {len(bars):3} bars")
        if bars:
            latest = bars[-1]
            print(f"              Latest: O:{latest.open:.2f} H:{latest.high:.2f} L:{latest.low:.2f} C:{latest.close:.2f}")
    
    # Test integration info
    print("\n🔍 Aggregation Info:")
    info = aggregator.get_aggregation_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Aggregator test completed!")
