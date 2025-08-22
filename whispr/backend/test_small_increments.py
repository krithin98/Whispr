#!/usr/bin/env python3
import asyncio
import aiohttp
import os
from datetime import datetime, timezone
from schwab_config import SchwabOAuthManager

async def test_small_increments():
    print("🧪 Testing Small Increments Past 10 Days...")
    
    oauth_manager = SchwabOAuthManager(
        client_id='aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1',
        client_secret='0dG11fLY8qF7iYz3',
        redirect_uri='https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
    )
    
    await oauth_manager.load_tokens()
    access_token = await oauth_manager.get_valid_access_token()
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Test small increments past 10 days for timeframes that worked
    test_cases = []
    
    # Test 1-minute data
    for days in [10, 11, 12, 13, 14]:
        test_cases.append(("1-minute", f"{days} days", {"symbol": "$SPX", "periodType": "day", "period": days, "frequencyType": "minute", "frequency": 1}))
    
    # Test 10-minute data  
    for days in [10, 11, 12, 13, 14]:
        test_cases.append(("10-minute", f"{days} days", {"symbol": "$SPX", "periodType": "day", "period": days, "frequencyType": "minute", "frequency": 10}))
    
    # Test 15-minute data
    for days in [10, 11, 12, 13, 14]:
        test_cases.append(("15-minute", f"{days} days", {"symbol": "$SPX", "periodType": "day", "period": days, "frequencyType": "minute", "frequency": 15}))
    
    # Test 30-minute data
    for days in [10, 11, 12, 13, 14]:
        test_cases.append(("30-minute", f"{days} days", {"symbol": "$SPX", "periodType": "day", "period": days, "frequencyType": "minute", "frequency": 30}))
    
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
                            frequency = 1 if timeframe == "1-minute" else int(timeframe.split('-')[0])
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
            await asyncio.sleep(0.3)

if __name__ == "__main__":
    asyncio.run(test_small_increments())
