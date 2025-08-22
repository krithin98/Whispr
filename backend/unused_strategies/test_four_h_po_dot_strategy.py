#!/usr/bin/env python3
"""
Test script for 4H PO Dot Strategy generation and evaluation.
"""

import asyncio
import json
from database import get_db, log_event
from four_h_po_dot_strategy import po_dot_strategy_generator
from indicators import phase_oscillator_indicator

async def test_po_dot_strategy_system():
    """Test the complete PO Dot strategy system."""
    
    print("🧪 Testing 4H PO Dot Strategy System")
    print("=" * 50)
    
    # 1. Generate PO Dot strategies
    print("\n1. Generating PO Dot strategies...")
    total_strategies = await po_dot_strategy_generator.generate_po_dot_strategies()
    print(f"✅ Generated {total_strategies} PO Dot strategies")
    
    # 2. List generated strategies
    print("\n2. Generated strategies:")
    conn = await get_db()
    cursor = await conn.execute(
        "SELECT id, name, strategy_expression, tags, priority FROM strategies WHERE strategy_type = 'po_dot' ORDER BY priority DESC, name"
    )
    strategies = await cursor.fetchall()
    
    for strategy_id, name, expression, tags, priority in strategies:
        print(f"   {strategy_id}: {name} (priority: {priority})")
        print(f"      Expression: {expression}")
        print(f"      Tags: {tags}")
    
    # 3. Test strategy evaluation with sample data
    print("\n3. Testing PO Dot strategy evaluation...")
    
    # Sample market data that would trigger a bullish cross
    # Previous oscillator value: -65.0 (in accumulation zone)
    # Current oscillator value: -60.0 (crossed up out of accumulation)
    sample_market_data = {
        "close_prices": {
            "4h": [4500.0, 4501.0, 4502.0, 4503.0, 4504.0, 4505.0, 4506.0, 4507.0, 4508.0, 4509.0, 4510.0, 4511.0, 4512.0, 4513.0, 4514.0, 4515.0, 4516.0, 4517.0, 4518.0, 4519.0, 4520.0]
        },
        "atr_values": {
            "4h": [15.0, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8, 15.9, 16.0, 16.1, 16.2, 16.3, 16.4]
        },
        "ema_21_values": {
            "4h": [4495.0, 4495.5, 4496.0, 4496.5, 4497.0, 4497.5, 4498.0, 4498.5, 4499.0, 4499.5, 4500.0, 4500.5, 4501.0, 4501.5, 4502.0, 4502.5, 4503.0, 4503.5, 4504.0, 4504.5, 4505.0]
        }
    }
    
    print(f"   Testing with sample market data for SPX 4H")
    
    # Get PO Dot strategies to test
    cursor = await conn.execute(
        "SELECT id, name, strategy_expression FROM strategies WHERE strategy_type = 'po_dot' LIMIT 1"
    )
    test_strategies = await cursor.fetchall()
    
    for strategy_id, strategy_name, expression in test_strategies:
        # Simulate the oscillator crossing up
        # First, set previous value in accumulation zone
        phase_oscillator_indicator.oscillator_history["4h"] = [-65.0]
        
        # Calculate current oscillator value (should be around -60.0, crossing up)
        oscillator_value = phase_oscillator_indicator.calculate_phase_oscillator(
            sample_market_data["close_prices"]["4h"],
            sample_market_data["atr_values"]["4h"],
            sample_market_data["ema_21_values"]["4h"]
        )
        
        print(f"     Oscillator value: {oscillator_value}")
        
        # Test the strategy evaluation
        result = await po_dot_strategy_generator.evaluate_po_dot_strategy(strategy_id, sample_market_data)
        
        if result.get("triggered", False):
            zone = result.get("zone", "unknown")
            print(f"     🚨 {strategy_name} TRIGGERED!")
            print(f"        Zone: {zone}, Oscillator: {oscillator_value}")
            print(f"        Message: {result.get('message', 'N/A')}")
        else:
            print(f"     ⏳ {strategy_name} - No trigger")
            if "error" in result:
                print(f"        Error: {result['error']}")
    
    # 4. Show strategy statistics
    print("\n4. PO Dot Strategy Statistics:")
    stats = await po_dot_strategy_generator.get_po_dot_statistics()
    print(f"   Total triggers: {stats['total_triggers']}")
    
    if stats['recent_triggers']:
        print(f"   Recent triggers: {len(stats['recent_triggers'])}")
        for trigger in stats['recent_triggers'][:3]:  # Show last 3
            print(f"     - {trigger.get('strategy_name', 'Unknown')}: {trigger.get('oscillator_value', 'N/A')} in {trigger.get('zone', 'unknown')} zone")
    else:
        print("   No recent triggers")
    
    # 5. Test Phase Oscillator calculation
    print("\n5. Testing Phase Oscillator calculation:")
    
    # Test different oscillator values and zones
    test_values = [-110.0, -80.0, -50.0, 0.0, 50.0, 80.0, 110.0]
    
    for value in test_values:
        zone = phase_oscillator_indicator.get_phase_zone(value)
        print(f"   Oscillator {value}: {zone} zone")
    
    print("\n✅ PO Dot strategy system test completed!")

async def test_phase_oscillator_indicator():
    """Test the Phase Oscillator indicator calculations."""
    print("\n🔧 Testing Phase Oscillator Indicator")
    print("=" * 40)
    
    # Test bullish cross detection
    print("\nTesting bullish cross detection:")
    
    # Test case 1: Crossing up from extreme down
    phase_oscillator_indicator.oscillator_history["4h"] = [-105.0]  # Previous in extreme down
    cross1 = phase_oscillator_indicator.detect_bullish_cross("4h", -95.0)  # Current above -100
    print(f"   Extreme down cross (-105 → -95): {'✅ TRIGGERED' if cross1 else '❌ No trigger'}")
    
    # Test case 2: Crossing up from accumulation
    phase_oscillator_indicator.oscillator_history["4h"] = [-70.0]  # Previous in accumulation
    cross2 = phase_oscillator_indicator.detect_bullish_cross("4h", -60.0)  # Current above -61.8
    print(f"   Accumulation cross (-70 → -60): {'✅ TRIGGERED' if cross2 else '❌ No trigger'}")
    
    # Test case 3: No cross (moving within same zone)
    phase_oscillator_indicator.oscillator_history["4h"] = [-50.0]  # Previous in mark down
    cross3 = phase_oscillator_indicator.detect_bullish_cross("4h", -45.0)  # Current still in mark down
    print(f"   No cross (-50 → -45): {'✅ TRIGGERED' if cross3 else '❌ No trigger'}")
    
    # Test case 4: Bearish cross (should not trigger)
    phase_oscillator_indicator.oscillator_history["4h"] = [80.0]  # Previous in distribution
    cross4 = phase_oscillator_indicator.detect_bullish_cross("4h", 70.0)  # Current below 61.8
    print(f"   Bearish cross (80 → 70): {'✅ TRIGGERED' if cross4 else '❌ No trigger'}")

if __name__ == "__main__":
    asyncio.run(test_phase_oscillator_indicator())
    asyncio.run(test_po_dot_strategy_system()) 