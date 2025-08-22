#!/usr/bin/env python3
"""
Test script for Schwab Streamer API integration.
This script demonstrates how to use the SchwabStreamerProvider for real-time market data.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from data_providers import DataProviderManager, DataProviderType, MarketData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def market_data_callback(market_data: MarketData):
    """Callback function for real-time market data updates"""
    print(f"🔄 {market_data.symbol}: ${market_data.price:.2f} "
          f"({market_data.change:+.2f}, {market_data.change_percent:+.2f}%) "
          f"Vol: {market_data.volume:,} "
          f"Bid: ${market_data.bid:.2f} Ask: ${market_data.ask:.2f}")

async def heartbeat_callback(heartbeat: str):
    """Callback function for heartbeat messages"""
    print(f"💓 Heartbeat: {heartbeat}")

async def test_schwab_streamer():
    """Test the Schwab Streamer integration"""
    
    # Check for required environment variables
    access_token = os.getenv("SCHWAB_ACCESS_TOKEN")
    customer_id = os.getenv("SCHWAB_CLIENT_CUSTOMER_ID")
    
    if not access_token or not customer_id:
        print("❌ Missing required environment variables:")
        print("   - SCHWAB_ACCESS_TOKEN")
        print("   - SCHWAB_CLIENT_CUSTOMER_ID")
        print("\n📝 To get these values:")
        print("   1. Complete Schwab Developer Portal application")
        print("   2. Use POST /token endpoint to get access token")
        print("   3. Use GET /user_preferences endpoint to get customer ID")
        print("   4. Set environment variables and run this script again")
        return
    
    print("🚀 Testing Schwab Streamer API Integration")
    print("=" * 50)
    
    # Create Schwab Streamer provider
    try:
        provider_manager = DataProviderManager(
            provider_type=DataProviderType.SCHWAB,
            access_token=access_token,
            schwab_client_customer_id=customer_id,
            schwab_client_channel="N9",
            schwab_client_function_id="APIAPP"
        )
        
        print("✅ Schwab Streamer provider created successfully")
        
        # Test connection
        print("\n🔌 Testing connection...")
        if isinstance(provider_manager.provider, provider_manager.provider.__class__):
            connected = await provider_manager.provider.connect()
            if connected:
                print("✅ Successfully connected to Schwab Streamer")
                
                # Subscribe to test symbols
                test_symbols = ["SPY", "QQQ", "AAPL", "TSLA"]
                print(f"\n📡 Subscribing to symbols: {test_symbols}")
                
                success = await provider_manager.subscribe_to_symbols(
                    test_symbols, 
                    market_data_callback
                )
                
                if success:
                    print("✅ Successfully subscribed to symbols")
                    print("\n📊 Starting data stream (press Ctrl+C to stop)...")
                    print("-" * 80)
                    
                    # Start streaming for 30 seconds
                    try:
                        await asyncio.wait_for(
                            provider_manager.start_streaming(),
                            timeout=30.0
                        )
                    except asyncio.TimeoutError:
                        print("\n⏰ Test completed after 30 seconds")
                    except KeyboardInterrupt:
                        print("\n⏹️  Test stopped by user")
                    
                    # Disconnect
                    await provider_manager.disconnect()
                    print("✅ Disconnected from Schwab Streamer")
                    
                else:
                    print("❌ Failed to subscribe to symbols")
            else:
                print("❌ Failed to connect to Schwab Streamer")
                print("   Check your access token and customer ID")
        
    except Exception as e:
        print(f"❌ Error creating Schwab Streamer provider: {e}")
        logger.exception("Detailed error:")

async def test_schwab_only_mode():
    """Test Schwab-only mode (no fallback)"""
    print("\n🎯 Testing Schwab-Only Mode")
    print("=" * 30)
    
    try:
        # Create Schwab provider without fallback
        provider_manager = DataProviderManager(DataProviderType.SCHWAB)
        
        # Test that methods exist but warn about missing implementation
        symbols = ["SPY", "QQQ", "AAPL", "TSLA"]
        for symbol in symbols:
            quote = await provider_manager.get_quote(symbol)
            if quote:
                print(f"✅ {symbol} Quote available")
            else:
                print(f"ℹ️ No {symbol} quote (expected - needs real Schwab connection)")
        
        # Test historical data (should show warning)
        print("\n📊 Testing historical data...")
        hist_data = await provider_manager.get_historical_data("SPY", period="1d", interval="5m")
        if hist_data is None:
            print("ℹ️ Historical data unavailable (expected - needs Schwab REST API)")
        else:
            print(f"✅ Got {len(hist_data)} historical data points")
        
        # Test option chain (should show warning)
        print("\n📋 Testing option chain...")
        options = await provider_manager.get_option_chain("SPY")
        if options is None:
            print("ℹ️ Option chain unavailable (expected - needs Schwab REST API)")
        else:
            print(f"✅ Got option chain")
        
        # Test market hours (should show warning)
        print("\n🕐 Testing market hours...")
        hours = await provider_manager.get_market_hours()
        if hours is None:
            print("ℹ️ Market hours unavailable (expected - needs Schwab REST API)")
        else:
            print(f"✅ Market hours available")
        
        print("✅ Schwab-only mode test completed")
        
    except Exception as e:
        print(f"❌ Error testing Schwab-only mode: {e}")
        logger.exception("Detailed error:")

async def main():
    """Main test function"""
    print("🧪 Whispr Data Provider Test Suite")
    print("=" * 50)
    
    # Test Schwab Streamer (if credentials available)
    await test_schwab_streamer()
    
    # Test Schwab-only mode
    await test_schwab_only_mode()
    
    print("\n✅ Test suite completed!")

if __name__ == "__main__":
    asyncio.run(main()) 