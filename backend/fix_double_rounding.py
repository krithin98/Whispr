#!/usr/bin/env python3
"""
Fix double rounding issue in ATR calculator
"""

# Read the current file
with open('atr_calculator.py', 'r') as f:
    content = f.read()

# Find and replace all the round() calls in the ATRLevels constructor
old_pattern = '''        return ATRLevels(
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
        )'''

new_pattern = '''        return ATRLevels(
            previous_close=previous_close,
            atr=atr,  # ATR already rounded
            timeframe=timeframe,
            lower_trigger=lower_trigger,  # No additional rounding
            upper_trigger=upper_trigger,
            lower_0382=lower_0382,
            upper_0382=upper_0382,
            lower_0500=lower_0500,
            upper_0500=upper_0500,
            lower_0618=lower_0618,
            upper_0618=upper_0618,
            lower_0786=lower_0786,
            upper_0786=upper_0786,
            lower_1000=lower_1000,
            upper_1000=upper_1000,
            lower_1236=lower_1236,
            upper_1236=upper_1236,
            lower_1618=lower_1618,
            upper_1618=upper_1618,
            lower_2000=lower_2000,
            upper_2000=upper_2000,
            true_range=true_range,
            tr_percent_of_atr=tr_percent_of_atr
        )'''

# Replace in the file
if old_pattern in content:
    new_content = content.replace(old_pattern, new_pattern)
    
    with open('atr_calculator.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Fixed double rounding issue!")
    print("🎯 Now matches Saty's ThinkScript approach:")
    print("   - ATR rounded once to 2 decimals")
    print("   - Levels calculated with full precision from rounded ATR")
else:
    print("❌ Could not find the pattern to replace")

