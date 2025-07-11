#!/usr/bin/env python3
"""
Test script for Golden Gate rule generation and evaluation.
"""

import asyncio
import json
from indicators import gg_rule_generator, indicator_manager
from database import get_db, log_event

async def test_golden_gate_system():
    """Test the complete Golden Gate rule system."""
    
    print("🧪 Testing Golden Gate Rule System")
    print("=" * 50)
    
    # 1. Generate Golden Gate rules
    print("\n1. Generating Golden Gate rules...")
    await gg_rule_generator.generate_golden_gate_rules()
    print("✅ Golden Gate rules generated")
    
    # 2. List generated rules
    print("\n2. Generated rules:")
    conn = await get_db()
    cursor = await conn.execute(
        "SELECT id, name, rule_expression, rule_type, indicator_ref FROM rules WHERE rule_type = 'golden_gate' ORDER BY name"
    )
    rules = await cursor.fetchall()
    
    for rule in rules:
        rule_id, name, expression, rule_type, indicator_ref = rule
        print(f"   - {name} (ID: {rule_id})")
        print(f"     Expression: {expression}")
        print(f"     Type: {rule_type}")
        print(f"     Indicator: {indicator_ref}")
    
    # 3. Test rule evaluation with sample data and time-based probabilities
    print("\n3. Testing rule evaluation with Day GG probabilities...")
    
    # Simulate different times of day
    from datetime import datetime, time
    
    test_scenarios = [
        (4500, datetime.now().replace(hour=9, minute=30, second=0), "Market Open"),
        (4510, datetime.now().replace(hour=10, minute=15, second=0), "10:00 AM"),
        (4520, datetime.now().replace(hour=11, minute=30, second=0), "11:30 AM"),
        (4530, datetime.now().replace(hour=14, minute=45, second=0), "2:45 PM"),
    ]
    
    symbol = "SPY"
    
    for price, test_time, time_description in test_scenarios:
        print(f"\n   Testing {time_description} (${price})")
        
        # Get Day GG rules specifically
        cursor = await conn.execute(
            "SELECT id, name, rule_expression FROM rules WHERE rule_type = 'golden_gate' AND name LIKE '%Day%' LIMIT 2"
        )
        test_rules = await cursor.fetchall()
        
        for rule_id, rule_name, expression in test_rules:
            result = await gg_rule_generator.evaluate_gg_rule(rule_id, price, symbol, test_time)
            if result.get("triggered", False):
                probability = result.get("completion_probability", 0)
                time_slot = result.get("time_slot", "unknown")
                print(f"     🚨 {rule_name} TRIGGERED!")
                print(f"        Price: ${price}, Level: {result.get('level', 'N/A')}")
                print(f"        Time Slot: {time_slot}")
                print(f"        Completion Probability: {probability:.1%}")
            else:
                print(f"     ⏳ {rule_name} - No trigger")
    
    # 4. Show recent events with enhanced logging
    print("\n4. Recent Golden Gate events:")
    cursor = await conn.execute(
        "SELECT event_type, payload FROM events WHERE event_type IN ('golden_gate_trigger', 'golden_gate_complete', 'golden_gate_pending') ORDER BY ts DESC LIMIT 8"
    )
    events = await cursor.fetchall()
    
    for event_type, payload in events:
        payload_data = json.loads(payload) if payload else {}
        if event_type == 'golden_gate_trigger':
            prob = payload_data.get('completion_probability', 0)
            time_slot = payload_data.get('time_slot', 'unknown')
            print(f"   🚨 {event_type}: {payload_data.get('rule_name', 'Unknown')} - {prob:.1%} completion rate ({time_slot})")
        elif event_type == 'golden_gate_complete':
            hours = payload_data.get('time_to_completion_hours', 0)
            print(f"   ✅ {event_type}: {payload_data.get('rule_name', 'Unknown')} - Completed in {hours:.1f} hours")
        elif event_type == 'golden_gate_pending':
            hours = payload_data.get('time_since_trigger_hours', 0)
            print(f"   ⏳ {event_type}: {payload_data.get('rule_name', 'Unknown')} - Pending for {hours:.1f} hours")
    
    print("\n✅ Enhanced Golden Gate system test completed!")

async def test_indicator_data_storage():
    """Test storing and retrieving indicator data."""
    
    print("\n🧪 Testing Indicator Data Storage")
    print("=" * 50)
    
    # Store some sample ATR data
    sample_data = {
        "previous_close": 4500.0,
        "atr": 40.0,
        "upper_0382": 4515.28,
        "upper_0618": 4524.72,
        "lower_0382": 4484.72,
        "lower_0618": 4475.28
    }
    
    await indicator_manager.store_indicator_data(
        "saty_atr_levels",
        "SPY",
        "day",
        sample_data
    )
    
    print("✅ Sample indicator data stored")
    
    # Retrieve the data
    retrieved_data = await indicator_manager.get_indicator_data(
        "saty_atr_levels",
        "SPY",
        "day"
    )
    
    if retrieved_data:
        print("✅ Indicator data retrieved successfully:")
        for key, value in retrieved_data.items():
            print(f"   {key}: {value}")
    else:
        print("❌ Failed to retrieve indicator data")

if __name__ == "__main__":
    asyncio.run(test_golden_gate_system())
    asyncio.run(test_indicator_data_storage()) 