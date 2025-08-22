#!/usr/bin/env python3
"""
Update bootstrap to use ALL available historical data instead of limiting to 100
"""

# Read the current file
with open('atr_system.py', 'r') as f:
    content = f.read()

# Find and replace the limit = 100 line
old_limit = 'limit = 100  # Get 100 bars for all timeframes'
new_limit = '''# Use ALL available data for maximum ATR accuracy
            optimal_limits = {
                "scalp": 3900,     # All 1-min data (10 days)
                "day": 5031,       # All daily data (20 years) 
                "multiday": 1043,  # All weekly data (20 years)
                "swing": 240,      # All monthly data (20 years)
                "position": 240,   # All monthly data (20 years)
                "long_term": 240   # All monthly data (20 years)
            }
            
            limit = optimal_limits.get(timeframe, 5000)  # Use optimal limits'''

# Replace in the file
if old_limit in content:
    new_content = content.replace(old_limit, new_limit)
    
    with open('atr_system.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Updated to use ALL available historical data!")
    print("📊 Now using 5,031 daily bars instead of 100")
    print("🎯 This will give much more accurate ATR calculations!")
else:
    print("❌ Could not find the limit line to replace")
    if "limit = 100" in content:
        print("  - Found limit = 100 in file")

