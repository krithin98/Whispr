#!/usr/bin/env python3
"""
Replace the bootstrap method in atr_system.py with database version
"""

# Read the current file
with open('atr_system.py', 'r') as f:
    content = f.read()

# Find and replace the bootstrap method
old_method = '''    async def _bootstrap_historical_data(self, timeframe: str) -> bool:
        """Bootstrap historical data for a timeframe using Schwab API"""
        try:
            logger.info(f"📊 Fetching historical SPX data for {timeframe} timeframe...")
            
            # Determine how much historical data we need based on timeframe
            timeframe_days = {
                "scalp": 3,      # 4H bars: need 3 days for 14+ bars  
                "day": 30,       # Daily bars: need 30 days for 14+ bars
                "multiday": 120, # Weekly bars: need ~4 months for 14+ bars
                "swing": 365,    # Monthly bars: need 1+ year for 14+ bars
                "position": 1095, # Quarterly: need 3+ years for 14+ bars
                "long_term": 4380 # Yearly: need 12+ years for 14+ bars
            }
            
            days_needed = timeframe_days.get(timeframe, 30)
            
            # Get minute data from Schwab (this will be our base data)
            minute_candles = await self.data_collector.get_minute_data("SPX", days=min(days_needed, 7))
            
            if not minute_candles:
                logger.warning(f"⚠️  No minute data received from Schwab for bootstrapping")
                return False
            
            logger.info(f"✅ Retrieved {len(minute_candles)} minute candles from Schwab")
            
            # Feed this historical minute data into our aggregator
            for candle in minute_candles:
                self.timeframe_aggregator.add_minute_bar(
                    candle.timestamp,
                    candle.open,
                    candle.high, 
                    candle.low,
                    candle.close,
                    candle.volume
                )
            
            # Verify we now have enough data
            historical_candles = self.timeframe_aggregator.get_timeframe_history(timeframe, periods=30)
            
            logger.info(f"📈 After bootstrap: {len(historical_candles)} {timeframe} bars available")
            
            return len(historical_candles) >= 14
            
        except Exception as e:
            logger.error(f"❌ Error bootstrapping historical data for {timeframe}: {e}")
            return False'''

new_method = '''    async def _bootstrap_historical_data(self, timeframe: str) -> bool:
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
            return False
    
    async def _process_minute_data_for_4h(self, minute_data: list):
        """Process 1-minute data into 4-hour bars for scalp timeframe"""
        from datetime import datetime
        for row in minute_data:
            timestamp_str, open_price, high_price, low_price, close_price, volume = row
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Feed into aggregator as minute bars
            self.timeframe_aggregator.add_minute_bar(
                timestamp, open_price, high_price, low_price, close_price, volume
            )
    
    async def _process_historical_bars(self, historical_data: list, timeframe: str):
        """Process historical bars directly for day/multiday/swing/position/long_term"""
        from datetime import datetime
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
                )'''

# Replace the method
if old_method in content:
    new_content = content.replace(old_method, new_method)
    
    # Write the updated content
    with open('atr_system.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Successfully replaced bootstrap method with database version!")
    print("🔄 Updated: API bootstrap → Database bootstrap")
else:
    print("❌ Could not find the old bootstrap method to replace")
    print("📊 Checking what we have:")
    if "Fetching historical SPX data" in content:
        print("  - Found old API bootstrap method")
    if "Loading historical data from database" in content:
        print("  - Found new database bootstrap method")
