#!/usr/bin/env python3
import asyncio
import os
from data_collector import SchwabDataCollector
from schwab_config import SchwabOAuthManager

async def test_maximum_data():
    print('🧪 Testing MAXIMUM Data Available...')
    
    os.environ['SCHWAB_CLIENT_ID'] = 'aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1'
    os.environ['SCHWAB_CLIENT_SECRET'] = '0dG11fLY8qF7iYz3'
    os.environ['SCHWAB_REDIRECT_URI'] = 'https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
    
    oauth_manager = SchwabOAuthManager(
        client_id='aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1',
        client_secret='0dG11fLY8qF7iYz3',
        redirect_uri='https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
    )
    
    collector = SchwabDataCollector(oauth_manager)
    
    # Test MAXIMUM amounts
    max_tests = [
        ("1-minute MAX", {"periodType": "day", "period": 10, "frequencyType": "minute", "frequency": 1}),
        ("Daily MAX", {"periodType": "year", "period": 20, "frequencyType": "daily", "frequency": 1}),
        ("Weekly MAX", {"periodType": "year", "period": 20, "frequencyType": "weekly", "frequency": 1}),
        ("Monthly MAX", {"periodType": "year", "period": 20, "frequencyType": "monthly", "frequency": 1}),
    ]
    
    for test_name, params in max_tests:
        print(f'\n📊 Testing {test_name}...')
        
        params_with_symbol = {
            "symbol": "$SPX",
            "needExtendedHoursData": "false",
            **params
        }
        
        try:
            response = await collector._make_api_request("/marketdata/v1/pricehistory", params_with_symbol)
            
            if "candles" in response and response["candles"]:
                candles = response["candles"]
                
                from datetime import datetime, timezone
                first_date = datetime.fromtimestamp(candles[0]["datetime"]/1000, timezone.utc).strftime('%Y-%m-%d')
                last_date = datetime.fromtimestamp(candles[-1]["datetime"]/1000, timezone.utc).strftime('%Y-%m-%d')
                
                years_span = len(candles) / (252 if 'Daily' in test_name else (52 if 'Weekly' in test_name else (12 if 'Monthly' in test_name else 390)))
                
                print(f'✅ {test_name}: {len(candles):,} candles')
                print(f'   Range: {first_date} to {last_date}')
                print(f'   Equivalent: ~{years_span:.1f} years of data')
                
            else:
                print(f'❌ {test_name}: No candles received')
                
        except Exception as e:
            print(f'❌ {test_name}: Error - {e}')

if __name__ == "__main__":
    asyncio.run(test_maximum_data())
