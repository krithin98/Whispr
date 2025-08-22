#!/usr/bin/env python3
"""
Database-Based Bootstrap for ATR System
Uses stored historical data instead of API calls
"""

import sqlite3
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class HistoricalCandle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

class DatabaseBootstrap:
    """Bootstrap ATR system using stored historical data"""
    
    def __init__(self, db_path: str = "/opt/spx-atr/data/spx_tracking.db"):
        self.db_path = db_path
        
    def get_historical_data(self, timeframe: str, limit: int = 1000) -> List[HistoricalCandle]:
        """Get historical data for a specific timeframe"""
        print(f"📊 Loading {timeframe} historical data from database...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Map our timeframes to stored timeframes
        timeframe_mapping = {
            "scalp": "1min_10d",      # Use 1-min for 4h aggregation
            "day": "daily_20y",       # Use daily data
            "multiday": "weekly_20y", # Use weekly data  
            "swing": "monthly_20y",   # Use monthly data
            "position": "monthly_20y", # Aggregate monthly to quarterly
            "long_term": "monthly_20y" # Aggregate monthly to yearly
        }
        
        db_timeframe = timeframe_mapping.get(timeframe, "daily_20y")
        
        cursor.execute("""
            SELECT timestamp, open_price, high_price, low_price, close_price, volume
            FROM historical_candles 
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (db_timeframe, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        candles = []
        for row in results:
            timestamp_str, open_price, high_price, low_price, close_price, volume = row
            
            # Parse timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            candles.append(HistoricalCandle(
                timestamp=timestamp,
                open=open_price,
                high=high_price, 
                low=low_price,
                close=close_price,
                volume=volume
            ))
            
        # Reverse to get chronological order (oldest first)
        candles.reverse()
        
        print(f"✅ Loaded {len(candles)} {timeframe} candles from {candles[0].timestamp.date()} to {candles[-1].timestamp.date()}")
        return candles
        
    def test_bootstrap(self):
        """Test bootstrap functionality"""
        print("🧪 Testing Database Bootstrap...")
        print("=" * 50)
        
        timeframes = ["scalp", "day", "multiday", "swing", "position", "long_term"]
        
        for timeframe in timeframes:
            try:
                candles = self.get_historical_data(timeframe, 100)
                if candles:
                    print(f"✅ {timeframe}: {len(candles)} candles available")
                    print(f"   Range: {candles[0].timestamp.date()} to {candles[-1].timestamp.date()}")
                    print(f"   Latest close: ${candles[-1].close}")
                else:
                    print(f"❌ {timeframe}: No data available")
                    
            except Exception as e:
                print(f"❌ {timeframe}: Error - {e}")
                
            print()

if __name__ == "__main__":
    bootstrap = DatabaseBootstrap()
    bootstrap.test_bootstrap()
