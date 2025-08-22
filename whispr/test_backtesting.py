#!/usr/bin/env python3
"""
Test script for the backtesting functionality
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.backtesting import backtesting_engine
from backend.database import get_db

async def test_backtesting():
    """Test the backtesting functionality"""
    print("🧪 Testing Backtesting Engine...")
    
    try:
        # Test 1: Get available strategies
        print("\n1. Testing strategy retrieval...")
        conn = await get_db()
        cursor = await conn.execute("SELECT id, name FROM strategies WHERE is_active = 1 LIMIT 3")
        strategies = await cursor.fetchall()
        
        if not strategies:
            print("❌ No strategies found in database")
            return
        
        strategy_ids = [s[0] for s in strategies]
        print(f"✅ Found {len(strategies)} strategies: {[s[1] for s in strategies]}")
        
        # Test 2: Run single strategy backtest
        print("\n2. Testing single strategy backtest...")
        result = await backtesting_engine.backtest_strategy(
            strategy_id=strategy_ids[0],
            symbol="SPY",
            start_date="2024-01-01",
            end_date="2024-03-31"
        )
        
        print(f"✅ Single backtest completed:")
        print(f"   Strategy: {result.strategy_name}")
        print(f"   Total Trades: {result.total_trades}")
        print(f"   Win Rate: {result.win_rate:.2f}%")
        print(f"   Total Return: {result.total_return:.2f}%")
        print(f"   Max Drawdown: {result.max_drawdown:.2f}%")
        print(f"   Sharpe Ratio: {result.sharpe_ratio:.2f}")
        
        # Test 3: Run multiple strategy backtest
        print("\n3. Testing multiple strategy backtest...")
        results = await backtesting_engine.backtest_multiple_strategies(
            strategy_ids=strategy_ids,
            symbol="SPY",
            start_date="2024-01-01",
            end_date="2024-03-31"
        )
        
        print(f"✅ Multiple backtest completed:")
        print(f"   Strategies tested: {len(results)}")
        for result in results:
            print(f"   - {result.strategy_name}: {result.total_return:.2f}% return, {result.win_rate:.2f}% win rate")
        
        # Test 4: Test historical data generation
        print("\n4. Testing historical data generation...")
        historical_data = await backtesting_engine.get_historical_data(
            symbol="SPY",
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        print(f"✅ Historical data generated:")
        print(f"   Data points: {len(historical_data)}")
        print(f"   Date range: {historical_data.iloc[0]['date']} to {historical_data.iloc[-1]['date']}")
        print(f"   Price range: ${historical_data['close'].min():.2f} - ${historical_data['close'].max():.2f}")
        
        print("\n🎉 All backtesting tests passed!")
        
    except Exception as e:
        print(f"❌ Backtesting test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_backtesting()) 