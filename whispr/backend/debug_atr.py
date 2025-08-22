import sqlite3

conn = sqlite3.connect('/opt/spx-atr/data/spx_tracking.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT timestamp, high_price, low_price, close_price
    FROM historical_candles 
    WHERE timeframe = "daily_20y"
    ORDER BY timestamp DESC
    LIMIT 16
''')

results = cursor.fetchall()
results.reverse()  # Chronological order

print('Last 16 days of data:')
for i, (timestamp, high, low, close) in enumerate(results):
    print(f'{i+1:2d}. {timestamp[:10]}: H={high:.2f} L={low:.2f} C={close:.2f}')

# Calculate True Ranges
true_ranges = []
for i in range(1, len(results)):
    prev_close = results[i-1][3]
    high = results[i][1]
    low = results[i][2]
    
    tr = max(high - low, abs(high - prev_close), abs(prev_close - low))
    true_ranges.append(tr)

print(f'\nTrue Ranges (last 15):')
for i, tr in enumerate(true_ranges):
    print(f'TR{i+1:2d}: {tr:.4f}')

# Method 1: Simple average of last 14
simple_14 = sum(true_ranges[-14:]) / 14
print(f'\nMethod 1 - Simple 14 avg: {simple_14:.6f}')

# Method 2: Wilder's with all data
first_atr = sum(true_ranges[:14]) / 14
wilder_atr = first_atr
for i in range(14, len(true_ranges)):
    wilder_atr = ((wilder_atr * 13) + true_ranges[i]) / 14
print(f'Method 2 - Our Wilder\'s: {wilder_atr:.6f}')

# Method 3: Exclude most recent (like ThinkScript [1])
if len(true_ranges) > 14:
    exclude_last = true_ranges[:-1]
    first_atr = sum(exclude_last[:14]) / 14
    wilder_prev = first_atr
    for i in range(14, len(exclude_last)):
        wilder_prev = ((wilder_prev * 13) + exclude_last[i]) / 14
    print(f'Method 3 - Exclude last: {wilder_prev:.6f}')

print(f'\nToS Target: 53.37')
