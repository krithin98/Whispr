#!/usr/bin/env python3
"""
Test script for strategy triggers functionality.
"""

import asyncio
import json
from database import get_db, log_strategy_trigger, get_strategy_triggers, update_trigger_outcome
from strategies import seed_test_strategies

async def test_strategy_triggers():
    """Test the strategy triggers functionality."""
    print("🧪 Testing Strategy Triggers System...")
    
    # Initialize database and seed test strategies
    await seed_test_strategies()
    
    # Test 1: Log a strategy trigger
    print("\n1. Testing strategy trigger logging...")
    try:
        await log_strategy_trigger(
            strategy_id=1,
            strategy_name="Test ATR Strategy",
            strategy_type="atr_based",
            symbol="SPY",
            timeframe="1d",
            trigger_type="entry",
            side="bull",
            price=450.50,
            confidence=0.85,
            conditions_met=["ATR level 2 break", "Price > 450"],
            market_data={
                "price": 450.50,
                "atr": 2.5,
                "volume": 1000000
            },
            notes="Test trigger for ATR strategy"
        )
        print("✅ Strategy trigger logged successfully")
    except Exception as e:
        print(f"❌ Failed to log strategy trigger: {e}")
        return
    
    # Test 2: Log another trigger with different type
    print("\n2. Testing another trigger type...")
    try:
        await log_strategy_trigger(
            strategy_id=2,
            strategy_name="Test Vomy Strategy",
            strategy_type="vomy_ivomy",
            symbol="SPX",
            timeframe="4h",
            trigger_type="signal",
            side="bear",
            price=5200.75,
            confidence=0.92,
            conditions_met=["13 EMA crossed below 48 EMA", "Volume > 500k"],
            market_data={
                "price": 5200.75,
                "ema_13": 5210.0,
                "ema_48": 5215.0,
                "volume": 750000
            }
        )
        print("✅ Second strategy trigger logged successfully")
    except Exception as e:
        print(f"❌ Failed to log second trigger: {e}")
    
    # Test 3: Retrieve triggers with filters
    print("\n3. Testing trigger retrieval with filters...")
    try:
        # Get all triggers
        all_triggers = await get_strategy_triggers(limit=10)
        print(f"✅ Retrieved {len(all_triggers)} triggers")
        
        # Get triggers by strategy type
        atr_triggers = await get_strategy_triggers(strategy_type="atr_based")
        print(f"✅ Retrieved {len(atr_triggers)} ATR triggers")
        
        # Get triggers by symbol
        spy_triggers = await get_strategy_triggers(symbol="SPY")
        print(f"✅ Retrieved {len(spy_triggers)} SPY triggers")
        
        # Get triggers by side
        bull_triggers = await get_strategy_triggers(side="bull")
        print(f"✅ Retrieved {len(bull_triggers)} bullish triggers")
        
    except Exception as e:
        print(f"❌ Failed to retrieve triggers: {e}")
    
    # Test 4: Update trigger outcome
    print("\n4. Testing trigger outcome update...")
    try:
        if all_triggers:
            trigger_id = all_triggers[0]["id"]
            await update_trigger_outcome(
                trigger_id=trigger_id,
                outcome="success",
                outcome_price=455.25,
                outcome_time="2024-01-15T14:30:00Z"
            )
            print(f"✅ Updated trigger {trigger_id} outcome to success")
        else:
            print("⚠️ No triggers found to update")
    except Exception as e:
        print(f"❌ Failed to update trigger outcome: {e}")
    
    # Test 5: Display trigger details
    print("\n5. Displaying trigger details...")
    try:
        triggers = await get_strategy_triggers(limit=5)
        for i, trigger in enumerate(triggers, 1):
            print(f"\nTrigger {i}:")
            print(f"  ID: {trigger['id']}")
            print(f"  Strategy: {trigger['strategy_name']} ({trigger['strategy_type']})")
            print(f"  Symbol: {trigger['symbol']} ({trigger['timeframe']})")
            print(f"  Type: {trigger['trigger_type']} - {trigger['side']}")
            print(f"  Price: ${trigger['price']}")
            print(f"  Confidence: {trigger['confidence']}")
            print(f"  Outcome: {trigger['outcome'] or 'Pending'}")
            print(f"  Timestamp: {trigger['timestamp']}")
            
            # Parse JSON fields
            try:
                conditions = json.loads(trigger['conditions_met']) if trigger['conditions_met'] else []
                print(f"  Conditions: {conditions}")
            except:
                print(f"  Conditions: {trigger['conditions_met']}")
        
        print(f"\n✅ Displayed {len(triggers)} trigger details")
        
    except Exception as e:
        print(f"❌ Failed to display trigger details: {e}")
    
    print("\n🎉 Strategy Triggers Test Complete!")

async def test_api_endpoints():
    """Test the API endpoints for strategy triggers."""
    print("\n🌐 Testing API Endpoints...")
    
    # This would require the FastAPI app to be running
    # For now, just show the expected endpoints
    endpoints = [
        "GET /strategy-triggers - Get all triggers with filters",
        "GET /strategy-triggers/{trigger_id} - Get specific trigger",
        "PUT /strategy-triggers/{trigger_id}/outcome - Update trigger outcome",
        "GET /strategy-triggers/analytics/summary - Get trigger analytics"
    ]
    
    print("Available endpoints:")
    for endpoint in endpoints:
        print(f"  {endpoint}")
    
    print("\n✅ API endpoints documented")

if __name__ == "__main__":
    asyncio.run(test_strategy_triggers())
    asyncio.run(test_api_endpoints()) 
