#!/usr/bin/env python3
"""
Test script for ATR strategy generation and evaluation.
"""

import asyncio
import json
from database import get_db, log_event
from strategy_engine import strategy_engine

async def test_atr_strategy_system():
    """Test the complete ATR strategy system."""
    
    print("🧪 Testing ATR Strategy System")
    
    # 1. Generate ATR strategies
    print("\n1. Generating ATR strategies...")
    total_strategies = await strategy_engine.generate_atr_strategies()
    print(f"✅ Generated {total_strategies} ATR strategies")
    
    # 2. List generated strategies by category
    print("\n2. Generated strategies by category:")
    
    conn = await get_db()
    
    # Adjacent strategies
    cursor = await conn.execute(
        "SELECT id, name, strategy_expression, tags, priority FROM strategies WHERE strategy_type = 'atr_based' AND tags LIKE '%atr_level%' ORDER BY priority DESC, name LIMIT 10"
    )
    adjacent_strategies = await cursor.fetchall()
    
    print(f"\n   Adjacent Strategies ({len(adjacent_strategies)} shown):")
    for strategy_id, name, expression, tags, priority in adjacent_strategies:
        print(f"     {strategy_id}: {name} (priority: {priority})")
    
    # Multi-level strategies
    cursor = await conn.execute(
        "SELECT id, name, strategy_expression, tags, priority FROM strategies WHERE strategy_type = 'atr_based' AND tags LIKE '%atr_multi%' ORDER BY priority DESC, name LIMIT 10"
    )
    multi_strategies = await cursor.fetchall()
    
    print(f"\n   Multi-Level Strategies ({len(multi_strategies)} shown):")
    for strategy_id, name, expression, tags, priority in multi_strategies:
        print(f"     {strategy_id}: {name} (priority: {priority})")
    
    # 3. Test strategy evaluation with sample data
    print("\n3. Testing ATR strategy evaluation...")
    
    # Sample market data
    price = 4500.0
    symbol = "SPY"
    
    print(f"   Testing with price: ${price}, symbol: {symbol}")
    
    # Get a few ATR strategies to test
    cursor = await conn.execute(
        "SELECT id, name, strategy_expression FROM strategies WHERE strategy_type = 'atr_based' LIMIT 3"
    )
    test_strategies = await cursor.fetchall()
    
    for strategy_id, strategy_name, expression in test_strategies:
        result = await strategy_engine.evaluate_atr_strategy(strategy_id, price, symbol)
        
        if result.get("triggered", False):
            strategy_type = result.get("strategy_type", "unknown")
            tag = result.get("tag", "unknown")
            print(f"     🚨 {strategy_name} TRIGGERED!")
            print(f"        Type: {strategy_type}, Tag: {tag}")
        else:
            print(f"     ⏳ {strategy_name} - No trigger")
    
    # 4. Show strategy statistics
    print("\n4. ATR Strategy Statistics:")
    
    # Count strategies by type
    cursor = await conn.execute(
        "SELECT COUNT(*) as count, tags FROM strategies WHERE strategy_type = 'atr_based' GROUP BY tags"
    )
    strategy_counts = await cursor.fetchall()
    
    for count, tags in strategy_counts:
        tags_data = json.loads(tags)
        strategy_type = tags_data[0]  # atr_level or atr_multi
        timeframe = tags_data[1]
        tag = tags_data[2]
        side = tags_data[3]
        print(f"   {strategy_type} - {timeframe} {tag} {side}: {count} strategies")
    
    # 5. Recent ATR strategy events
    print("\n5. Recent ATR strategy events:")
    
    cursor = await conn.execute(
        "SELECT event_type, payload FROM events WHERE event_type = 'atr_strategy_trigger' ORDER BY ts DESC LIMIT 5"
    )
    events = await cursor.fetchall()
    
    for event_type, payload_json in events:
        payload_data = json.loads(payload_json)
        strategy_name = payload_data.get('strategy_expression', 'Unknown')
        strategy_type = payload_data.get('strategy_type', 'unknown')
        print(f"   {event_type}: {strategy_name} ({strategy_type})")

async def test_atr_configuration():
    """Test ATR configuration loading."""
    print("\n🔧 Testing ATR Configuration")
    
    # Load and display configuration
    spec = strategy_engine.get_atr_specification()
    
    print(f"✅ Loaded {len(spec['adjacent_strategies'])} adjacent strategy types")
    print(f"✅ Loaded {len(spec['multi_level_strategies'])} multi-level strategy types")
    
    # Show some example strategies
    print("\nExample Adjacent Strategies:")
    for tag, strategy_spec in list(spec['adjacent_strategies'].items())[:3]:
        print(f"   {tag}: {strategy_spec['description']}")
    
    print("\nExample Multi-Level Strategies:")
    for tag, strategy_spec in list(spec['multi_level_strategies'].items())[:3]:
        print(f"   {tag}: {strategy_spec['description']}")

if __name__ == "__main__":
    asyncio.run(test_atr_strategy_system())
    asyncio.run(test_atr_configuration()) 