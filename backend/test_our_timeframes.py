#!/usr/bin/env python3
import asyncio
import aiohttp
import os
from datetime import datetime, timezone
from schwab_config import SchwabOAuthManager

async def test_our_timeframes():
    print("🧪 Testing OUR Specific Timeframes...")
    
    oauth_manager = SchwabOAuthManager(
        client_id='aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1',
        client_secret='0dG11fLY8qF7iYz3',
        redirect_uri='https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
    )
    
    await oauth_manager.load_tokens()
    access_token = await oauth_manager.get_valid_access_token()
    
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://api.schwabapi.com"
    
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Test YOUR specific timeframes: 1m/3m/10m/1hr/4h/1d/1w
    test_cases = [
        # 1-minute (we know this works)
        {"periodType": "day", "period": "10", "frequencyType": "minute", "frequency": "1", "desc": "1-minute (10 days)"},
        
        # 3-minute 
        {"periodType": "day", "period": "10", "frequencyType": "minute", "frequency": "3", "desc": "3-minute (10 days)"},
        
        # 10-minute
        {"periodType": "day", "period": "10", "frequencyType": "minute", "frequency": "10", "desc": "10-minute (10 days)"},
        {"periodType": "month", "period": "1", "frequencyType": "minute", "frequency": "10", "desc": "10-minute (1 month)"},
        
        # 1-hour (test different periods)
        {"periodType": "month", "period": "1", "frequencyType": "minute", "frequency": "60", "desc": "1-hour (1 month)"},
        {"periodType": "month", "period": "3", "frequencyType": "minute", "frequency": "60", "desc": "1-hour (3 months)"},
        {"periodType": "month", "period": "6", "frequencyType": "minute", "frequency": "60", "desc": "1-hour (6 months)"},
        
        # 4-hour (this might not exist natively)
        {"periodType": "month", "period": "3", "frequencyType": "minute", "frequency": "240", "desc": "4-hour (3 months)"},
        
        # Daily (we know this works)
        {"periodType": "year", "period": "1", "frequencyType": "daily", "frequency": "1", "desc": "Daily (1 year)"},
        
        # Weekly
        {"periodType": "year", "period": "1", "frequencyType": "weekly", "frequency": "1", "desc": "Weekly (1 year)"},
        {"periodType": "year", "period": "2", "frequencyType": "weekly", "frequency": "1", "desc": "Weekly (2 years)"},
    ]
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        for test_case in test_cases:
            try:
                print(f"📊 Testing {test_case['desc']}...")
                
                params = {
                    "symbol": "$SPX",
                    "periodType": test_case["periodType"],
                    "period": test_case["period"],
                    "frequencyType": test_case["frequencyType"],
                    "frequency": test_case["frequency"]
                }
                
                url = f"{base_url}/marketdata/v1/pricehistory"
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        candle_count = len(data.get("candles", []))
                        print(f"✅ {test_case['desc']}: {candle_count} candles")
                        
                        if candle_count > 0:
                            first = data["candles"][0]
                            last = data["candles"][-1]
                            first_dt = datetime.fromtimestamp(first["datetime"] / 1000, timezone.utc)
                            last_dt = datetime.fromtimestamp(last["datetime"] / 1000, timezone.utc)
                            print(f"   Range: {first_dt.date()} to {last_dt.date()}")
                    else:
                        error_text = await response.text()
                        print(f"❌ {test_case['desc']} failed: {response.status}")
                        
            except Exception as e:
                print(f"❌ {test_case['desc']} error: {e}")

if __name__ == "__main__":
    asyncio.run(test_our_timeframes())
