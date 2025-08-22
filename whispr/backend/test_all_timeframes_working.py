#!/usr/bin/env python3
import asyncio
import os
from data_collector import SchwabDataCollector
from schwab_config import SchwabOAuthManager

async def test_all_timeframes():
    print('🧪 Testing All Schwab Timeframes...')
    
    # Set environment variables
    os.environ['SCHWAB_CLIENT_ID'] = 'aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1'
    os.environ['SCHWAB_CLIENT_SECRET'] = '0dG11fLY8qF7iYz3'
    os.environ['SCHWAB_REDIRECT_URI'] = 'https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
    
    oauth_manager = SchwabOAuthManager(
        client_id='aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1',
        client_secret='0dG11fLY8qF7iYz3',
        redirect_uri='https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
    )
    
    collector = SchwabDataCollector(oauth_manager)
    
    # Test various timeframes
    test_cases = [
        # Intraday timeframes (10 days max)
        ("1-minute", {"periodType": "day", "period": 3, "frequencyType": "minute", "frequency": 1}),
        ("10-minute", {"periodType": "day", "period": 3, "frequencyType": "minute", "frequency": 10}),
        ("15-minute", {"periodType": "day", "period": 3, "frequencyType": "minute", "frequency": 15}),
        ("30-minute", {"periodType": "day", "period": 3, "frequencyType": "minute", "frequency": 30}),
        
        # Longer timeframes
        ("Daily", {"periodType": "month", "period": 3, "frequencyType": "daily", "frequency": 1}),
        ("Weekly", {"periodType": "year", "period": 1, "frequencyType": "weekly", "frequency": 1}),
        ("Monthly", {"periodType": "year", "period": 2, "frequencyType": "monthly", "frequency": 1}),
    ]
    
    for timeframe_name, params in test_cases:
        print(f'\n📊 Testing {timeframe_name}...')
        
        params_with_symbol = {
            "symbol": "$SPX",
            "needExtendedHoursData": "false",
            **params
        }
        
        try:
            response = await collector._make_api_request("/marketdata/v1/pricehistory", params_with_symbol)
            
            if "candles" in response and response["candles"]:
                candles = response["candles"]
                first_time = candles[0]["datetime"]
                last_time = candles[-1]["datetime"]
                
                from datetime import datetime, timezone
                first_date = datetime.fromtimestamp(first_time/1000, timezone.utc).strftime('%Y-%m-%d %H:%M')
                last_date = datetime.fromtimestamp(last_time/1000, timezone.utc).strftime('%Y-%m-%d %H:%M')
                
                print(f'✅ {timeframe_name}: {len(candles)} candles')
                print(f'   Range: {first_date} to {last_date}')
                print(f'   Sample price: ${candles[-1]["close"]}')
            else:
                print(f'❌ {timeframe_name}: No candles received')
                
        except Exception as e:
            print(f'❌ {timeframe_name}: Error - {e}')

if __name__ == "__main__":
    asyncio.run(test_all_timeframes())
