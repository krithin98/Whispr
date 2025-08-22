#!/usr/bin/env python3
"""
Correct Bootstrap Strategy - Feed data directly to appropriate timeframes
"""

# Read the current file
with open('atr_system.py', 'r') as f:
    content = f.read()

# Replace the entire bootstrap method with the correct approach
old_bootstrap = '''    async def _bootstrap_historical_data(self, timeframe: str) -> bool:
        """Bootstrap historical data from database instead of API"""
        try:
            logger.info(f"📊 Loading historical data from database for {timeframe} timeframe...")
            
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
            import sqlite3
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
                
            # Verify we now have enough data
            historical_candles = self.timeframe_aggregator.get_timeframe_history(timeframe, periods=30)
            logger.info(f"📈 After bootstrap: {len(historical_candles)} {timeframe} bars available")
            
            return len(historical_candles) >= 14
            
        except Exception as e:
            logger.error(f"❌ Database bootstrap failed for {timeframe}: {e}")
            return False'''

new_bootstrap = '''    async def _bootstrap_historical_data(self, timeframe: str) -> bool:
        """Bootstrap historical data from database - feed directly to aggregator cache"""
        try:
            logger.info(f"📊 Loading historical data from database for {timeframe} timeframe...")
            
            # Map timeframes to database timeframes
            timeframe_mapping = {
                "scalp": "1min_10d",      # Use 1-min for 4h aggregation (only this needs aggregation)
                "day": "daily_20y",       # Direct: daily data → daily timeframe
                "multiday": "weekly_20y", # Direct: weekly data → multiday timeframe  
                "swing": "monthly_20y",   # Direct: monthly data → swing timeframe
                "position": "monthly_20y", # Will aggregate monthly → quarterly
                "long_term": "monthly_20y" # Will aggregate monthly → yearly
            }
            
            db_timeframe = timeframe_mapping.get(timeframe, "daily_20y")
            limit = 100  # Get 100 bars for all timeframes
            
            # Connect to database
            import sqlite3
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
            
            # Convert to OHLCBar objects and feed directly to the aggregator cache
            from dataclasses import dataclass
            from datetime import datetime
            from typing import List
            
            bars = []
            for row in results:
                timestamp_str, open_price, high_price, low_price, close_price, volume = row
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                
                # Create OHLCBar object
                bar = OHLCBar(
                    timestamp=timestamp,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                    timeframe=timeframe
                )
                bars.append(bar)
            
            # Special handling for scalp (needs aggregation from 1-min)
            if timeframe == "scalp":
                # Feed 1-min data for aggregation to 4h
                for bar in bars:
                    self.timeframe_aggregator.add_minute_bar(
                        bar.timestamp, bar.open, bar.high, bar.low, bar.close, bar.volume
                    )
            else:
                # Feed directly to the aggregator cache for this timeframe
                self.timeframe_aggregator.aggregated_cache[timeframe] = bars
            
            logger.info(f"📈 Bootstrap complete: {len(bars)} {timeframe} bars loaded")
            return len(bars) >= 14
            
        except Exception as e:
            logger.error(f"❌ Database bootstrap failed for {timeframe}: {e}")
            return False'''

# Replace the method
if old_bootstrap in content:
    new_content = content.replace(old_bootstrap, new_bootstrap)
    
    # Write the updated content
    with open('atr_system.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Implemented CORRECT bootstrap strategy!")
    print("🎯 Now feeds data directly to appropriate timeframe caches")
    print("📊 Only scalp (1min→4h) uses aggregation, others are direct")
else:
    print("❌ Could not find the bootstrap method to replace")

