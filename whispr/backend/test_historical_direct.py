#!/usr/bin/env python3
import asyncio
from data_collector import get_data_collector

async def test_historical():
    print('🧪 Testing Historical Data Fetch Directly...')
    
    collector = await get_data_collector()
    
    # Test minute data fetch
    print('📊 Testing 1-minute data for 3 days...')
    try:
        candles = await collector.get_minute_data('SPX', days=3)
        print(f'✅ Received {len(candles)} minute candles')
        if candles:
            print(f'   First: {candles[0].timestamp} - ${candles[0].close}')
            print(f'   Last: {candles[-1].timestamp} - ${candles[-1].close}')
    except Exception as e:
        print(f'❌ Error: {e}')
    
    # Test daily data fetch  
    print('📊 Testing daily data for 30 days...')
    try:
        daily_candles = await collector.get_daily_data('SPX', days=30)
        print(f'✅ Received {len(daily_candles)} daily candles')
        if daily_candles:
            print(f'   First: {daily_candles[0].timestamp} - ${daily_candles[0].close}')
            print(f'   Last: {daily_candles[-1].timestamp} - ${daily_candles[-1].close}')
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    asyncio.run(test_historical())
