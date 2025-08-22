#!/usr/bin/env python3
"""
Fix the bootstrap method to use add_minute_bar for all timeframes
"""

# Read the current file
with open('atr_system.py', 'r') as f:
    content = f.read()

# Find the problematic method calls and replace them
old_process_method = '''    async def _process_historical_bars(self, historical_data: list, timeframe: str):
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

new_process_method = '''    async def _process_historical_bars(self, historical_data: list, timeframe: str):
        """Process historical bars - convert all to minute bars for aggregation"""
        from datetime import datetime
        logger.info(f"🔄 Processing {len(historical_data)} {timeframe} bars into minute format...")
        
        for row in historical_data:
            timestamp_str, open_price, high_price, low_price, close_price, volume = row
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # All historical data goes through add_minute_bar
            # The aggregator will handle timeframe conversion automatically
            self.timeframe_aggregator.add_minute_bar(
                timestamp, open_price, high_price, low_price, close_price, volume
            )
        
        logger.info(f"✅ Processed {len(historical_data)} historical bars for {timeframe}")'''

# Replace the method
if old_process_method in content:
    new_content = content.replace(old_process_method, new_process_method)
    
    # Write the updated content
    with open('atr_system.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Fixed bootstrap method to use add_minute_bar for all data!")
    print("🔄 All timeframes now use the same aggregation path")
else:
    print("❌ Could not find the method to replace")
    if "_process_historical_bars" in content:
        print("  - Found _process_historical_bars method")
    if "add_daily_bar" in content:
        print("  - Found add_daily_bar calls")
