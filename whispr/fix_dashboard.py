#!/usr/bin/env python3

# Read the broken dashboard file
with open('production_dashboard.py', 'r') as f:
    lines = f.readlines()

# Fix the indentation issues and imports
fixed_lines = []
for i, line in enumerate(lines):
    if 'from data_collector import SchwabDataCollector' in line and not line.startswith('    '):
        # This line is incorrectly indented, skip it and the next ones
        continue
    elif 'from schwab_config import get_oauth_manager' in line and not line.startswith('    '):
        continue
    elif 'collector = SchwabDataCollector(get_oauth_manager())' in line and not line.startswith('    '):
        continue
    elif line.strip() == 'def get_live_price():':
        # Replace the entire function with a working version
        fixed_lines.append('def get_live_price():\n')
        fixed_lines.append('    """Get current SPX price."""\n')
        fixed_lines.append('    try:\n')
        fixed_lines.append('        from data_collector import SchwabDataCollector\n')
        fixed_lines.append('        from schwab_config import get_oauth_manager\n')
        fixed_lines.append('        collector = SchwabDataCollector(get_oauth_manager())\n')
        fixed_lines.append('        tick = collector.get_current_price("SPX")\n')
        fixed_lines.append('        return tick.price\n')
        fixed_lines.append('    except Exception as e:\n')
        fixed_lines.append('        print(f"Live price error: {e}")\n')
        fixed_lines.append('        return None\n')
        fixed_lines.append('\n')
        # Skip until we find the next function or section
        j = i + 1
        while j < len(lines) and (lines[j].startswith('    ') or lines[j].strip() == ''):
            j += 1
        i = j - 1
        continue
    else:
        fixed_lines.append(line)

# Write the fixed file
with open('production_dashboard.py', 'w') as f:
    f.writelines(fixed_lines)

print("✅ Dashboard file fixed!")
