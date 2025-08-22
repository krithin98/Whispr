#!/usr/bin/env python3
import asyncio
import aiohttp
import os
from datetime import datetime, timezone
from schwab_config import SchwabOAuthManager

async def test_max_historical():
    print("🧪 Testing Maximum Schwab Historical Data Range...")
    
    oauth_manager = SchwabOAuthManager(
        client_id='aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1',
        client_secret='0dG11fLY8qF7iYz3',
        redirect_uri='https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
    )
    
    await oauth_manager.load_tokens()
    access_token = await oauth_manager.get_valid_access_token()
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Test increasingly longer periods for daily data
    test_cases = [
        ("Daily", "2 years", {"symbol": "$SPX", "periodType": "year", "period": 2, "frequencyType": "daily", "frequency": 1}),
        ("Daily", "3 years", {"symbol": "$SPX", "periodType": "year", "period": 3, "frequencyType": "daily", "frequency": 1}),
        ("Daily", "5 years", {"symbol": "$SPX", "periodType": "year", "period": 5, "frequencyType": "daily", "frequency": 1}),
        ("Daily", "10 years", {"symbol": "$SPX", "periodType": "year", "period": 10, "frequencyType": "daily", "frequency": 1}),
        ("Daily", "20 years", {"symbol": "$SPX", "periodType": "year", "period": 20, "frequencyType": "daily", "frequency": 1}),
        ("Weekly", "5 years", {"symbol": "$SPX", "periodType": "year", "period": 5, "frequencyType": "weekly", "frequency": 1}),
        ("Weekly", "10 years", {"symbol": "$SPX", "periodType": "year", "period": 10, "frequencyType": "weekly", "frequency": 1}),
        ("Weekly", "20 years", {"symbol": "$SPX", "periodType": "year", "period": 20, "frequencyType": "weekly", "frequency": 1}),
        ("Monthly", "5 years", {"symbol": "$SPX", "periodType": "year", "period": 5, "frequencyType": "monthly", "frequency": 1}),
        ("Monthly", "10 years", {"symbol": "$SPX", "periodType": "year", "period": 10, "frequencyType": "monthly", "frequency": 1}),
        ("Monthly", "20 years", {"symbol": "$SPX", "periodType": "year", "period": 20, "frequencyType": "monthly", "frequency": 1}),
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
                            years_span = len(candles) / (252 if timeframe == "Daily" else (52 if timeframe == "Weekly" else 12))
                            print(f"✅ {timeframe} ({period_desc}): {len(candles)} candles")
                            print(f"   Range: {first_date} to {last_date} (~{years_span:.1f} years)")
                        else:
                            print(f"❌ {timeframe} ({period_desc}): No candles returned")
                    else:
                        print(f"❌ {timeframe} ({period_desc}) failed: {response.status}")
                        
            except Exception as e:
                print(f"❌ {timeframe} ({period_desc}) error: {e}")
            
            # Small delay between requests
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(test_max_historical())
