#!/usr/bin/env python3
"""
Test script to stream live market data from Whispr data providers
"""

import asyncio
import os
import sys
from datetime import datetime
from data_providers import get_provider, DataProviderManager, DataProviderType

async def test_live_data_stream():
    """Test streaming live market data."""
    print("🚀 Whispr Data Stream Test")
    print("=" * 50)
    
    # Get the data provider (Schwab only)
    try:
        provider = get_provider("schwab")
        print(f"📊 Using provider: {provider.__class__.__name__}")
    except Exception as e:
        print(f"❌ Failed to initialize Schwab provider: {e}")
        print("💡 Make sure Schwab credentials are configured")
        return
    
    # Test symbols
    symbols = ["SPY", "QQQ", "AAPL", "TSLA"]
    
    print(f"\n📈 Testing quotes for: {', '.join(symbols)}")
    print("-" * 50)
    
    try:
        for i in range(3):  # Test 3 times
            print(f"\n🕐 Test #{i+1} - {datetime.now().strftime('%H:%M:%S')}")
            
            for symbol in symbols:
                try:
                    # Get latest quote
                    quote = await provider.get_quote(symbol)
                    
                    if quote:
                        print(f"  {symbol:>6}: ${quote.price:>8.2f} (Bid: ${quote.bid:>6.2f}, Ask: ${quote.ask:>6.2f})")
                    else:
                        print(f"  {symbol:>6}: No quote available")
                    
                except Exception as e:
                    print(f"  {symbol:>6}: Error - {str(e)}")
            
            # Wait 5 seconds between tests
            if i < 2:  # Don't wait after the last test
                print("⏳ Waiting 5 seconds...")
                await asyncio.sleep(5)
                
    except KeyboardInterrupt:
        print("\n\n⏹️  Test stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
    
    print("\n✅ Quote test completed!")

async def test_streaming_connection():
    """Test Schwab streaming connection."""
    print("\n📡 Testing Schwab Streaming Connection")
    print("=" * 40)
    
    try:
        # Create Schwab provider with credentials
        provider = DataProviderManager(DataProviderType.SCHWAB)
        
        # Test connection
        if hasattr(provider.provider, 'connect'):
            connected = await provider.provider.connect()
            if connected:
                print("✅ Successfully connected to Schwab Streamer")
                
                # Test subscription
                symbols = ["SPY"]
                success = await provider.subscribe_to_symbols(symbols)
                if success:
                    print(f"✅ Successfully subscribed to {symbols}")
                else:
                    print(f"❌ Failed to subscribe to {symbols}")
                
                # Disconnect
                await provider.provider.disconnect()
                print("✅ Successfully disconnected")
            else:
                print("❌ Failed to connect to Schwab Streamer")
        else:
            print("ℹ️ Provider doesn't support streaming connection")
            
    except Exception as e:
        print(f"❌ Streaming test error: {str(e)}")

async def main():
    """Main test function."""
    print("🎯 Whispr Schwab Data Provider Test Suite")
    print("=" * 50)
    
    # Test 1: Quote data
    await test_live_data_stream()
    
    # Test 2: Streaming connection
    await test_streaming_connection()
    
    print("\n🎉 All tests completed!")
    print("\n💡 Note: This test uses simulated Schwab data.")
    print("   Configure real Schwab credentials for live data.")

if __name__ == "__main__":
    asyncio.run(main()) 
