#!/usr/bin/env python3
import asyncio
import aiohttp
import os
from datetime import datetime, timezone
from schwab_config import SchwabOAuthManager

async def test_10min_limits():
    print("🧪 Testing 10-Minute Data Limits Specifically...")
    
    oauth_manager = SchwabOAuthManager(
        client_id='aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1',
        client_secret='0dG11fLY8qF7iYz3',
        redirect_uri='https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
    )
    
    await oauth_manager.load_tokens()
    access_token = await oauth_manager.get_valid_access_token()
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Test 10-minute data with increasingly longer periods
    test_cases = [
        ("10-minute", "10 days", {"symbol": "$SPX", "periodType": "day", "period": 10, "frequencyType": "minute", "frequency": 10}),
        ("10-minute", "15 days", {"symbol": "$SPX", "periodType": "day", "period": 15, "frequencyType": "minute", "frequency": 10}),
        ("10-minute", "20 days", {"symbol": "$SPX", "periodType": "day", "period": 20, "frequencyType": "minute", "frequency": 10}),
        ("10-minute", "25 days", {"symbol": "$SPX", "periodType": "day", "period": 25, "frequencyType": "minute", "frequency": 10}),
        ("10-minute", "30 days", {"symbol": "$SPX", "periodType": "day", "period": 30, "frequencyType": "minute", "frequency": 10}),
        ("10-minute", "1 month", {"symbol": "$SPX", "periodType": "month", "period": 1, "frequencyType": "minute", "frequency": 10}),
        ("10-minute", "2 months", {"symbol": "$SPX", "periodType": "month", "period": 2, "frequencyType": "minute", "frequency": 10}),
        ("10-minute", "3 months", {"symbol": "$SPX", "periodType": "month", "period": 3, "frequencyType": "minute", "frequency": 10}),
        ("10-minute", "6 months", {"symbol": "$SPX", "periodType": "month", "period": 6, "frequencyType": "minute", "frequency": 10}),
        
        # Also test other timeframes that worked before
        ("15-minute", "10 days", {"symbol": "$SPX", "periodType": "day", "period": 10, "frequencyType": "minute", "frequency": 15}),
        ("15-minute", "15 days", {"symbol": "$SPX", "periodType": "day", "period": 15, "frequencyType": "minute", "frequency": 15}),
        ("15-minute", "20 days", {"symbol": "$SPX", "periodType": "day", "period": 20, "frequencyType": "minute", "frequency": 15}),
        
        ("30-minute", "10 days", {"symbol": "$SPX", "periodType": "day", "period": 10, "frequencyType": "minute", "frequency": 30}),
        ("30-minute", "15 days", {"symbol": "$SPX", "periodType": "day", "period": 15, "frequencyType": "minute", "frequency": 30}),
        ("30-minute", "20 days", {"symbol": "$SPX", "periodType": "day", "period": 20, "frequencyType": "minute", "frequency": 30}),
        ("30-minute", "30 days", {"symbol": "$SPX", "periodType": "day", "period": 30, "frequencyType": "minute", "frequency": 30}),
    ]
    
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        for timeframe, period_desc, params in test_cases:
            print(f"📊 Testing {timeframe} ({period_desc})...")
            
            try:
                async with session.get(
                    "https://api.schwabapi.com/marketdata/v1/pricehistory",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        candles = data.get('candles', [])
                        if candles:
                            first_date = datetime.fromtimestamp(candles[0]['datetime']/1000, tz=timezone.utc).strftime('%Y-%m-%d')
                            last_date = datetime.fromtimestamp(candles[-1]['datetime']/1000, tz=timezone.utc).strftime('%Y-%m-%d')
                            frequency = int(timeframe.split('-')[0])  # Extract number from "10-minute"
                            trading_days = len(candles) * frequency / 390  # 390 minutes per trading day
                            print(f"✅ {timeframe} ({period_desc}): {len(candles)} candles")
                            print(f"   Range: {first_date} to {last_date} (~{trading_days:.1f} trading days)")
                        else:
                            print(f"❌ {timeframe} ({period_desc}): No candles returned")
                    else:
                        print(f"❌ {timeframe} ({period_desc}) failed: {response.status}")
                        
            except Exception as e:
                print(f"❌ {timeframe} ({period_desc}) error: {e}")
            
            # Small delay between requests
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(test_10min_limits())
