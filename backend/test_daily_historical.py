#!/usr/bin/env python3
import asyncio
import aiohttp
import os
from datetime import datetime, timezone
from schwab_config import SchwabOAuthManager

async def test_daily_data():
    print("🧪 Testing Schwab Daily Historical Data...")
    
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
    
    test_cases = [
        {"period": "6", "periodType": "month", "frequencyType": "daily", "desc": "6 months daily"},
        {"period": "1", "periodType": "year", "frequencyType": "daily", "desc": "1 year daily"},
        {"period": "2", "periodType": "year", "frequencyType": "daily", "desc": "2 years daily"},
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
                    "frequency": "1"
                }
                
                url = f"{base_url}/marketdata/v1/pricehistory"
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        candle_count = len(data.get("candles", []))
                        print(f"✅ {test_case['desc']}: {candle_count} daily candles")
                        
                        if candle_count > 0:
                            first = data["candles"][0]
                            last = data["candles"][-1]
                            first_dt = datetime.fromtimestamp(first["datetime"] / 1000, timezone.utc)
                            last_dt = datetime.fromtimestamp(last["datetime"] / 1000, timezone.utc)
                            print(f"   Range: {first_dt.date()} to {last_dt.date()}")
                    else:
                        error_text = await response.text()
                        print(f"❌ {test_case['desc']} failed: {response.status}")
                        print(f"   Error: {error_text}")
                        
            except Exception as e:
                print(f"❌ {test_case['desc']} error: {e}")

if __name__ == "__main__":
    asyncio.run(test_daily_data())
