#!/usr/bin/env python3
"""
Script to clear existing strategies and reseed with proper real strategies
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import get_db

async def reseed_strategies():
    """Clear existing strategies and reseed with proper ones."""
    print("🔄 Reseeding strategies...")
    
    try:
        conn = await get_db()
        
        # Clear existing strategies
        print("🗑️  Clearing existing strategies...")
        await conn.execute("DELETE FROM strategies")
        
        # Define real trading strategies
        real_strategies = [
            ("ATR Strategy", "True", "ATR-based strategy triggered. Check ATR levels and volatility conditions.", "atr_based"),
            ("Vomy Strategy", "True", "Vomy strategy activated. Analyze volume and momentum indicators.", "vomy_ivomy"),
            ("4H PO Dot Strategy", "True", "4-Hour Phase Oscillator Dot strategy triggered. Check trend direction.", "po_dot"),
            ("Conviction Arrow Strategy", "True", "Conviction Arrow signal detected. Evaluate market conviction.", "conviction_arrow"),
            ("Golden Gate Strategy", "True", "Golden Gate pattern identified. Check timing and completion probabilities.", "golden_gate")
        ]
        
        # Insert real strategies
        print("🌱 Seeding real strategies...")
        for name, expr, tpl, strategy_type in real_strategies:
            await conn.execute(
                "INSERT INTO strategies (name, strategy_expression, prompt_tpl, strategy_type, is_active) VALUES (?, ?, ?, ?, ?)",
                (name, expr, tpl, strategy_type, True)
            )
            print(f"   ✅ Added: {name} ({strategy_type})")
        
        # Verify the strategies were created
        cursor = await conn.execute("SELECT id, name, strategy_type FROM strategies WHERE is_active = 1")
        strategies = await cursor.fetchall()
        
        print(f"\n✅ Successfully seeded {len(strategies)} strategies:")
        for strategy in strategies:
            print(f"   - {strategy[1]} ({strategy[2]})")
        
        print("\n🎉 Strategy reseeding completed!")
        
    except Exception as e:
        print(f"❌ Failed to reseed strategies: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reseed_strategies()) 