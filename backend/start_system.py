#!/usr/bin/env python3
import asyncio
import os
import sys
from datetime import datetime
from atr_system import SPXATRSystem

async def main():
    print("🚀 Starting SPX ATR System...")
    
    # Set environment variables (exactly what works)
    os.environ['SCHWAB_CLIENT_ID'] = 'aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1'
    os.environ['SCHWAB_CLIENT_SECRET'] = '0dG11fLY8qF7iYz3'
    os.environ['SCHWAB_REDIRECT_URI'] = 'https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
    os.environ['DATABASE_PATH'] = '/opt/spx-atr/data/spx_tracking.db'
    os.environ['LOG_LEVEL'] = 'INFO'
    
    # Initialize the system
    system = SPXATRSystem()
    success = await system.initialize()
    
    if not success:
        print("❌ Failed to initialize system")
        sys.exit(1)
    
    print("✅ System initialized successfully, starting continuous operation...")
    
    # Keep running - this is the exact same pattern that worked in testing
    tick_count = 0
    while True:
        try:
            # Get SPX tick using the method that already works
            tick = await system.data_collector.get_current_price("SPX")
            
            if tick:
                # Validate tick has all required fields
                required_fields = ['symbol', 'price', 'high', 'low', 'volume', 'timestamp']
                missing_fields = [field for field in required_fields if not hasattr(tick, field)]
                
                if missing_fields:
                    print(f"❌ MarketTick missing fields: {missing_fields}")
                else:
                    # Process the tick - this is the exact same call that worked
                    hits = await system.process_market_tick(tick)
                    tick_count += 1
                    
                    print(f"📊 #{tick_count} Processed SPX: ${tick.price:.2f} (H: ${tick.high:.2f}, L: ${tick.low:.2f}, V: {tick.volume:,})")
                    
                    if hits:
                        print(f"🎯 Level hits detected: {len(hits)}")
            else:
                print("⚠️ No tick data received from Schwab API")
                
            # Wait 1 minute between updates (standard interval)
            await asyncio.sleep(60)
            
        except KeyboardInterrupt:
            print("🛑 Shutting down...")
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            print("🔄 Retrying in 10 seconds...")
            await asyncio.sleep(10)
    
    print("✅ SPX ATR System shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Received interrupt signal")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
