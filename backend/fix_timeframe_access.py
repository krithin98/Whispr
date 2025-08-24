#!/usr/bin/env python3
"""
Fix timeframe data access to use cached data
"""

# Read the timeframe aggregator file
with open('timeframe_aggregator.py', 'r') as f:
    content = f.read()

old_method = '''    def get_timeframe_history(self, timeframe: str, periods: int = 14) -> List[OHLCBar]:
        """
        Get recent history for a timeframe (useful for ATR calculation)
        Args:
            timeframe: One of your 6 timeframes
            periods: Number of recent bars to return
        """
        aggregated = self.get_aggregated_timeframes()
        
        if timeframe in aggregated and aggregated[timeframe]:
            return aggregated[timeframe][-periods:]
        
        return []'''

new_method = '''    def get_timeframe_history(self, timeframe: str, periods: int = 14) -> List[OHLCBar]:
        """
        Get recent history for a timeframe (useful for ATR calculation)
        Args:
            timeframe: One of your 6 timeframes
            periods: Number of recent bars to return
        """
        # First check if we have cached data (from database bootstrap)
        if timeframe in self.aggregated_cache and self.aggregated_cache[timeframe]:
            cached_data = self.aggregated_cache[timeframe]
            return cached_data[-periods:] if len(cached_data) >= periods else cached_data
        
        # Fallback to aggregated data (from live minute data)
        aggregated = self.get_aggregated_timeframes()
        
        if timeframe in aggregated and aggregated[timeframe]:
            return aggregated[timeframe][-periods:]
        
        return []'''

# Replace the method
if old_method in content:
    new_content = content.replace(old_method, new_method)
    
    with open('timeframe_aggregator.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Fixed get_timeframe_history to check cache first!")
    print("🎯 Now prioritizes cached database data over live aggregation")
else:
    print("❌ Could not find the method to replace")

