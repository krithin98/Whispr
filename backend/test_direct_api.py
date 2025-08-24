#!/usr/bin/env python3
import asyncio
import os
from data_collector import SchwabDataCollector
from schwab_config import SchwabOAuthManager

async def test_direct():
    print('🧪 Testing Direct API Call...')
    
    # Set environment variables
    os.environ['SCHWAB_CLIENT_ID'] = 'aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1'
    os.environ['SCHWAB_CLIENT_SECRET'] = '0dG11fLY8qF7iYz3'
    os.environ['SCHWAB_REDIRECT_URI'] = 'https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
    
    # Create OAuth manager and data collector
    oauth_manager = SchwabOAuthManager(
        client_id='aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1',
        client_secret='0dG11fLY8qF7iYz3',
        redirect_uri='https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
    )
    
    collector = SchwabDataCollector(oauth_manager)
    
    # Test the _make_api_request method directly
    params = {
        "symbol": "$SPX",
        "periodType": "day",
        "period": 1,
        "frequencyType": "minute", 
        "frequency": 1,
        "needExtendedHoursData": "false"
    }
    
    print('Calling _make_api_request directly with params:', params)
    
    try:
        response = await collector._make_api_request("/marketdata/v1/pricehistory", params)
        print('✅ Success! Response keys:', list(response.keys()) if response else 'No response')
        if 'candles' in response:
            print(f'   Got {len(response["candles"])} candles')
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    asyncio.run(test_direct())
