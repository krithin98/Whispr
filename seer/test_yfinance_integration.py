#!/usr/bin/env python3
"""
Test script for yfinance integration.
This script tests the YFinanceFeed class to ensure it can fetch real SPY data.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from data_feeds import YFinanceFeed
from backtesting import BacktestingEngine

async def test_yfinance_feed():
    """Test the YFinanceFeed class."""
    print("🧪 Testing YFinanceFeed integration...")
    
    # Test 1: Basic connection
    print("\n1. Testing YFinanceFeed connection...")
    spy_feed = YFinanceFeed("SPY")
    
    connected = await spy_feed.connect()
    if connected:
        print("✅ Successfully connected to yfinance")
        print(f"   Base price: ${spy_feed.base_price}")
    else:
        print("❌ Failed to connect to yfinance")
        return False
    
    # Test 2: Get latest data
    print("\n2. Testing latest data fetch...")
    tick_data = await spy_feed.get_latest_data()
    
    if tick_data:
        print("✅ Successfully fetched latest SPY data:")
        print(f"   Price: ${tick_data['price']}")
        print(f"   Volume: {tick_data['volume']:,}")
        print(f"   Change: {tick_data['change']:+.2f} ({tick_data['change_percent']:+.3f}%)")
        print(f"   Source: {tick_data['source']}")
        print(f"   Timestamp: {tick_data['timestamp']}")
    else:
        print("❌ Failed to fetch latest data")
        return False
    
    # Test 3: Historical data
    print("\n3. Testing historical data fetch...")
    historical_data = await spy_feed.get_historical_data(
        start_date="2024-01-01",
        end_date="2024-01-31",
        interval="1d"
    )
    
    if not historical_data.empty:
        print("✅ Successfully fetched historical data:")
        print(f"   Data points: {len(historical_data)}")
        print(f"   Date range: {historical_data.iloc[0]['date']} to {historical_data.iloc[-1]['date']}")
        print(f"   Price range: ${historical_data['close'].min():.2f} - ${historical_data['close'].max():.2f}")
        print(f"   Sample data:")
        print(historical_data.head(3).to_string(index=False))
    else:
        print("❌ Failed to fetch historical data")
        return False
    
    # Test 4: Backtesting engine with real data
    print("\n4. Testing backtesting engine with real data...")
    backtesting_engine = BacktestingEngine()
    
    historical_data = await backtesting_engine.get_historical_data(
        symbol="SPY",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
    
    if not historical_data.empty:
        print("✅ Backtesting engine successfully loaded real data:")
        print(f"   Data points: {len(historical_data)}")
        print(f"   Date range: {historical_data.iloc[0]['date']} to {historical_data.iloc[-1]['date']}")
        print(f"   Price range: ${historical_data['close'].min():.2f} - ${historical_data['close'].max():.2f}")
    else:
        print("❌ Backtesting engine failed to load real data")
        return False
    
    # Test 5: Stream simulation (just a few ticks)
    print("\n5. Testing data stream (3 ticks)...")
    tick_count = 0
    async for tick_data in spy_feed.stream():
        tick_count += 1
        print(f"   Tick {tick_count}: ${tick_data['price']} ({tick_data['change']:+.2f})")
        
        if tick_count >= 3:
            break
    
    await spy_feed.disconnect()
    print("✅ Data stream test completed")
    
    print("\n🎉 All yfinance integration tests passed!")
    return True

async def main():
    """Main test function."""
    try:
        success = await test_yfinance_feed()
        if success:
            print("\n✅ yfinance integration is working correctly!")
            print("   You can now use real SPY data in your trading system.")
        else:
            print("\n❌ yfinance integration tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 