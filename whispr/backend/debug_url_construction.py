#!/usr/bin/env python3
import asyncio
from data_collector import get_data_collector
from urllib.parse import urlencode

async def debug_url():
    print('🔍 Debugging URL Construction...')
    
    # Test the URL construction logic
    params = {
        "symbol": "$SPX",
        "periodType": "day", 
        "period": 3,
        "frequencyType": "minute",
        "frequency": 1,
        "needExtendedHoursData": "false"
    }
    
    print('Original params:', params)
    
    # Test our URL encoding
    if params and 'symbol' in params and params['symbol'] == '$SPX':
        print('✅ Detected $SPX symbol')
        params_copy = params.copy()
        params_copy['symbol'] = '%24SPX'
        query_string = urlencode(params_copy)
        url = f"https://api.schwabapi.com/marketdata/v1/pricehistory?{query_string}"
        print('Constructed URL:', url)
    
    # Now test with actual data collector
    collector = await get_data_collector()
    print('\n🧪 Testing actual API call...')
    
    try:
        candles = await collector.get_minute_data('SPX', days=1)
        print(f'Result: {len(candles)} candles')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(debug_url())
