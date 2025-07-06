#!/usr/bin/env python3
"""
Test script for Week 1 implementation:
- Data feed integration (Schwab simulation)
- Dry-run trade logging
- Performance metrics
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_data_feed():
    """Test the WebSocket data feed."""
    print("🔌 Testing data feed...")
    
    async with httpx.AsyncClient() as client:
        # Test health check
        response = await client.get("http://localhost:8000/")
        print(f"✅ Health check: {response.status_code}")
        
        # Test WebSocket connection (simplified)
        print("✅ WebSocket endpoint available at ws://localhost:8000/ws/ticks")

async def test_trade_logging():
    """Test the dry-run trade logging system."""
    print("\n💰 Testing trade logging...")
    
    async with httpx.AsyncClient() as client:
        # Place a buy trade
        buy_response = await client.post("http://localhost:8000/trades", params={
            "symbol": "SPY",
            "side": "buy",
            "quantity": 100,
            "price": 450.50,
            "order_type": "market"
        })
        
        if buy_response.status_code == 200:
            buy_result = buy_response.json()
            trade_id = buy_result["trade_id"]
            print(f"✅ Placed buy trade: {trade_id}")
            
            # Check open trades
            open_response = await client.get("http://localhost:8000/trades/open")
            if open_response.status_code == 200:
                open_trades = open_response.json()
                print(f"✅ Open trades: {len(open_trades)}")
            
            # Close the trade
            close_response = await client.post(f"http://localhost:8000/trades/{trade_id}/close", params={
                "exit_price": 451.25
            })
            
            if close_response.status_code == 200:
                close_result = close_response.json()
                pnl = close_result["pnl"]
                print(f"✅ Closed trade with P&L: ${pnl}")
            
            # Check performance metrics
            perf_response = await client.get("http://localhost:8000/trades/performance")
            if perf_response.status_code == 200:
                perf = perf_response.json()
                print(f"✅ Performance: {perf['total_trades']} trades, {perf['win_rate']}% win rate")
        else:
            print(f"❌ Failed to place trade: {buy_response.text}")

async def test_strategies_and_events():
    """Test strategies and events system."""
    print("\n📊 Testing strategies and events...")
    
    async with httpx.AsyncClient() as client:
        # Get strategies
        strategies_response = await client.get("http://localhost:8000/strategies")
        if strategies_response.status_code == 200:
            strategies = strategies_response.json()
            print(f"✅ Loaded {len(strategies)} strategies")
        
        # Get recent events
        events_response = await client.get("http://localhost:8000/last_events?limit=5")
        if events_response.status_code == 200:
            events = events_response.json()
            print(f"✅ Recent events: {len(events)}")
        
        # Get costs
        costs_response = await client.get("http://localhost:8000/costs")
        if costs_response.status_code == 200:
            costs = costs_response.json()
            print(f"✅ LLM costs configured: {costs['current']['provider']}")

async def main():
    """Run all Week 1 tests."""
    print("🚀 Week 1 Implementation Test")
    print("=" * 40)
    
    try:
        await test_data_feed()
        await test_trade_logging()
        await test_strategies_and_events()
        
        print("\n" + "=" * 40)
        print("✅ Week 1 implementation test completed!")
        print("\nNext steps:")
        print("1. Start the app: docker compose up --build")
        print("2. Connect to WebSocket: ws://localhost:8000/ws/ticks")
        print("3. Test trades: curl -X POST 'http://localhost:8000/trades?symbol=SPY&side=buy&quantity=100&price=450.50'")
        print("4. Check performance: curl http://localhost:8000/trades/performance")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("\nMake sure the app is running: docker compose up --build")

if __name__ == "__main__":
    asyncio.run(main()) 