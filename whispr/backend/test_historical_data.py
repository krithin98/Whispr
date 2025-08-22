#!/usr/bin/env python3
import asyncio
import aiohttp
import json
import os
from datetime import datetime, timezone
from schwab_config import SchwabOAuthManager

async def test_schwab_historical():
    print("🧪 Testing Schwab Historical Data API...")
    
    # Set environment variables
    os.environ['SCHWAB_CLIENT_ID'] = 'aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1'
    os.environ['SCHWAB_CLIENT_SECRET'] = '0dG11fLY8qF7iYz3'
    os.environ['SCHWAB_REDIRECT_URI'] = 'https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
    
    # Initialize OAuth manager with proper parameters
    oauth_manager = SchwabOAuthManager(
        client_id='aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1',
        client_secret='0dG11fLY8qF7iYz3',
        redirect_uri='https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
    )
    
    await oauth_manager.load_tokens()
    access_token = await oauth_manager.get_valid_access_token()
    
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    
    # Test different time periods
    base_url = "https://api.schwabapi.com"
    
    # Create SSL context that ignores certificate verification
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    test_cases = [
        {"days": 1, "desc": "1 day"},
        {"days": 5, "desc": "5 days"},
        {"days": 10, "desc": "10 days"},
        {"days": 30, "desc": "30 days"},
    ]
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        for test_case in test_cases:
            try:
                print(f"📊 Testing {test_case['desc']}...")
                
                # Try the API call with proper string parameters
                params = {
                    "symbol": "$SPX",
                    "periodType": "day",
                    "period": str(test_case["days"]),
                    "frequencyType": "minute", 
                    "frequency": "1",
                    "needExtendedHoursData": "false"  # String, not boolean
                }
                
                url = f"{base_url}/marketdata/v1/pricehistory"
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        candle_count = len(data.get("candles", []))
                        print(f"✅ {test_case['desc']}: {candle_count} minute candles")
                        
                        if candle_count > 0:
                            sample = data["candles"][0]
                            dt = datetime.fromtimestamp(sample["datetime"] / 1000, timezone.utc)
                            print(f"   Sample: {dt} OHLC: {sample['open']}/{sample['high']}/{sample['low']}/{sample['close']}")
                    else:
                        error_text = await response.text()
                        print(f"❌ {test_case['desc']} failed: {response.status}")
                        print(f"   Error: {error_text}")
                        
            except Exception as e:
                print(f"❌ {test_case['desc']} error: {e}")
    
    print("🎯 Historical data test complete!")

if __name__ == "__main__":
    asyncio.run(test_schwab_historical())
