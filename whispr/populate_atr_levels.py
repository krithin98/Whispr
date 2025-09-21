#!/usr/bin/env python3
"""
Populate ATR levels for testing
Using Friday's close as PDC and estimated ATR values
"""
import asyncio
import aiosqlite
import json
from datetime import date
from pathlib import Path

DB_PATH = Path("data/whispr.db")

# Friday's SPX close and estimated ATR values for different timeframes
ATR_DATA = {
    '5m': {'pdc': 6664.36, 'atr': 8.5},      # ~8-10 points for 5min
    '15m': {'pdc': 6664.36, 'atr': 15.0},    # ~15-20 points for 15min
    '30m': {'pdc': 6664.36, 'atr': 22.0},    # ~20-25 points for 30min
    '1h': {'pdc': 6664.36, 'atr': 35.0},     # ~30-40 points for 1h
    '2h': {'pdc': 6664.36, 'atr': 45.0},     # ~40-50 points for 2h
    '4h': {'pdc': 6664.36, 'atr': 60.0},     # ~55-65 points for 4h
    'daily': {'pdc': 6664.36, 'atr': 85.0},  # ~80-90 points for daily
    'weekly': {'pdc': 6664.36, 'atr': 180.0} # ~150-200 points for weekly
}

async def populate_atr_levels():
    """Populate ATR levels in database"""
    session_date = date.today().isoformat()

    conn = await aiosqlite.connect(DB_PATH)

    for timeframe, data in ATR_DATA.items():
        # Calculate Fibonacci levels
        atr = data['atr']
        pdc = data['pdc']

        levels_dict = {
            # Upper levels
            'upper_trigger': pdc + (atr * 0.236),
            'upper_0382': pdc + (atr * 0.382),
            'upper_0500': pdc + (atr * 0.500),
            'upper_0618': pdc + (atr * 0.618),
            'upper_0786': pdc + (atr * 0.786),
            'upper_1000': pdc + atr,
            'upper_1236': pdc + (atr * 1.236),
            'upper_1382': pdc + (atr * 1.382),
            'upper_1500': pdc + (atr * 1.500),
            'upper_1618': pdc + (atr * 1.618),
            'upper_1786': pdc + (atr * 1.786),
            'upper_2000': pdc + (atr * 2.000),

            # PDC (neutral)
            'PDC': pdc,

            # Lower levels
            'lower_trigger': pdc - (atr * 0.236),
            'lower_0382': pdc - (atr * 0.382),
            'lower_0500': pdc - (atr * 0.500),
            'lower_0618': pdc - (atr * 0.618),
            'lower_0786': pdc - (atr * 0.786),
            'lower_1000': pdc - atr,
            'lower_1236': pdc - (atr * 1.236),
            'lower_1382': pdc - (atr * 1.382),
            'lower_1500': pdc - (atr * 1.500),
            'lower_1618': pdc - (atr * 1.618),
            'lower_1786': pdc - (atr * 1.786),
            'lower_2000': pdc - (atr * 2.000),
        }

        # Store in database
        await conn.execute("""
            INSERT OR REPLACE INTO atr_levels
            (timeframe, session_date, calculation_time, previous_close, atr_value,
             lower_trigger, upper_trigger, lower_0382, upper_0382,
             lower_0500, upper_0500, lower_0618, upper_0618,
             lower_0786, upper_0786, lower_1000, upper_1000,
             lower_1236, upper_1236, lower_1618, upper_1618,
             lower_2000, upper_2000)
            VALUES (?, ?, datetime('now'), ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?)
        """, (timeframe, session_date, pdc, atr,
              levels_dict['lower_trigger'], levels_dict['upper_trigger'],
              levels_dict['lower_0382'], levels_dict['upper_0382'],
              levels_dict['lower_0500'], levels_dict['upper_0500'],
              levels_dict['lower_0618'], levels_dict['upper_0618'],
              levels_dict['lower_0786'], levels_dict['upper_0786'],
              levels_dict['lower_1000'], levels_dict['upper_1000'],
              levels_dict['lower_1236'], levels_dict['upper_1236'],
              levels_dict['lower_1618'], levels_dict['upper_1618'],
              levels_dict['lower_2000'], levels_dict['upper_2000']))

        print(f"✅ Populated {timeframe}: PDC=${pdc:.2f}, ATR=${atr:.2f}")

    await conn.commit()
    await conn.close()
    print(f"\n📊 All ATR levels populated for {session_date}")

if __name__ == "__main__":
    asyncio.run(populate_atr_levels())