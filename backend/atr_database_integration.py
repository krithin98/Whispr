#!/usr/bin/env python3
"""
Integrate Database Bootstrap into ATR System
Replace API-based bootstrap with database-based bootstrap
"""

import sqlite3
from datetime import datetime, timezone
from typing import List
from dataclasses import dataclass

@dataclass 
class HistoricalCandle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

def create_database_bootstrap_method():
    """Create the new bootstrap method that uses database instead of API"""
    
    bootstrap_code = '''
    async def _bootstrap_historical_data_from_db(self, timeframe: str) -> bool:
        """
        Bootstrap historical data from database instead of API
        Uses stored historical candles for ATR calculations
        """
        logger.info(f"📊 Loading historical data from database for {timeframe} timeframe...")
        
        try:
            # Map timeframes to database timeframes
            timeframe_mapping = {
                "scalp": "1min_10d",      # Use 1-min for 4h aggregation
                "day": "daily_20y",       # Use daily data
                "multiday": "weekly_20y", # Use weekly data  
                "swing": "monthly_20y",   # Use monthly data
                "position": "monthly_20y", # Aggregate monthly to quarterly
                "long_term": "monthly_20y" # Aggregate monthly to yearly
            }
            
            db_timeframe = timeframe_mapping.get(timeframe, "daily_20y")
            
            # Determine how much data we need
            timeframe_limits = {
                "scalp": 500,     # 500 1-min bars for 4h aggregation
                "day": 100,       # 100 daily bars
                "multiday": 100,  # 100 weekly bars
                "swing": 100,     # 100 monthly bars
                "position": 100,  # 100 monthly bars (will aggregate)
                "long_term": 100  # 100 monthly bars (will aggregate)
            }
            
            limit = timeframe_limits.get(timeframe, 100)
            
            # Connect to database
            conn = sqlite3.connect("/opt/spx-atr/data/spx_tracking.db")
            cursor = conn.cursor()
            
            # Get historical data
            cursor.execute("""
                SELECT timestamp, open_price, high_price, low_price, close_price, volume
                FROM historical_candles 
                WHERE timeframe = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (db_timeframe, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                logger.warning(f"⚠️  No historical data found for {timeframe} ({db_timeframe})")
                return False
            
            logger.info(f"✅ Retrieved {len(results)} historical candles for {timeframe}")
            
            # Process data based on timeframe
            if timeframe == "scalp":
                # For scalp (4h), aggregate 1-min data into 4h bars
                await self._process_minute_data_for_4h(results)
            else:
                # For other timeframes, use data directly
                await self._process_historical_bars(results, timeframe)
                
            logger.info(f"✅ Bootstrap complete for {timeframe} with {len(results)} bars")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database bootstrap failed for {timeframe}: {e}")
            return False
    
    async def _process_minute_data_for_4h(self, minute_data: List):
        """Process 1-minute data into 4-hour bars for scalp timeframe"""
        for row in minute_data:
            timestamp_str, open_price, high_price, low_price, close_price, volume = row
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Feed into aggregator as minute bars
            self.timeframe_aggregator.add_minute_bar(
                timestamp, open_price, high_price, low_price, close_price, volume
            )
    
    async def _process_historical_bars(self, historical_data: List, timeframe: str):
        """Process historical bars directly for day/multiday/swing/position/long_term"""
        for row in historical_data:
            timestamp_str, open_price, high_price, low_price, close_price, volume = row
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Feed directly into the appropriate timeframe aggregator
            if timeframe == "day":
                self.timeframe_aggregator.add_daily_bar(
                    timestamp, open_price, high_price, low_price, close_price, volume
                )
            elif timeframe == "multiday":
                self.timeframe_aggregator.add_weekly_bar(
                    timestamp, open_price, high_price, low_price, close_price, volume
                )
            elif timeframe in ["swing", "position", "long_term"]:
                self.timeframe_aggregator.add_monthly_bar(
                    timestamp, open_price, high_price, low_price, close_price, volume
                )
    '''
    
    return bootstrap_code

print("🔧 Database Bootstrap Integration Ready!")
print("="*50)
print("This will replace the API-based bootstrap in atr_system.py")
print("with a database-based bootstrap that uses our stored historical data.")
print("\nNext step: Replace _bootstrap_historical_data method in atr_system.py")
