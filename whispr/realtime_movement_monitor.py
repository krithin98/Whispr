#!/usr/bin/env python3
"""
Real-time Movement Monitoring System
Combines level detection with movement tracking for live analysis
"""
import asyncio
import aiosqlite
import logging
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Dict, List
import sys

# Add backend to path for imports
sys.path.append('backend')

from backend.comprehensive_level_detector import ComprehensiveLevelCalculator
from backend.realtime_level_detector import RealtimeLevelHitDetector
from backend.movement_tracker import MovementTracker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = Path("data/whispr.db")

class RealtimeMovementMonitor:
    """Monitors SPX movements in real-time"""

    def __init__(self):
        self.detector = RealtimeLevelHitDetector()
        self.tracker = MovementTracker()
        self.conn = None
        self.last_price = None
        self.monitoring = True

    async def initialize(self):
        """Initialize all components"""
        await self.detector.initialize()
        await self.tracker.initialize()
        self.conn = await aiosqlite.connect(DB_PATH)
        logger.info("✅ Real-time movement monitor initialized")

    async def simulate_price_movements(self):
        """Simulate price movements for testing"""
        # Starting at PDC (6664.36), simulate movements
        test_prices = [
            6664.36,  # PDC
            6665.50,  # Moving up
            6666.37,  # Hit upper_trigger (5m)
            6667.00,  # Continue up
            6667.61,  # Hit upper_0382 (5m)
            6668.50,  # Moving higher
            6669.61,  # Hit upper_0618 (5m) - Golden Gate complete!
            6668.00,  # Pull back
            6666.50,  # Pull back more
            6664.36,  # Back to PDC
            6663.00,  # Below PDC
            6662.35,  # Hit lower_trigger (5m)
            6661.11,  # Hit lower_0382 (5m)
            6659.11,  # Hit lower_0618 (5m) - Bear Golden Gate!
        ]

        for i, price in enumerate(test_prices):
            timestamp = datetime.now(timezone.utc).isoformat()
            logger.info(f"\n{'='*60}")
            logger.info(f"📊 PRICE TICK #{i+1}: ${price:.2f}")

            # Process through level detector
            hits = await self.detector.process_price_tick(price, timestamp)

            if hits:
                for hit in hits:
                    logger.info(f"🎯 LEVEL HIT: {hit['level_name']} [{hit['timeframe']}]")

                    # Process through movement tracker
                    movement = await self.tracker.process_new_hit(hit)

                    if movement:
                        logger.info(
                            f"🔗 MOVEMENT: {movement.from_level} → {movement.to_level} | "
                            f"Direction: {movement.direction} | "
                            f"Velocity: {movement.velocity:.2f} levels/min"
                        )

                        if movement.pattern_type:
                            logger.info(f"🌟 PATTERN DETECTED: {movement.pattern_type}")

            # Show position analysis
            position_5m = self.detector.calculator.get_price_position(price, '5m')
            if position_5m:
                logger.info(
                    f"📍 Position [5m]: Zone: {position_5m['current_zone']} | "
                    f"ATR Multiple: {position_5m['atr_multiple']:.3f}"
                )

            # Small delay between ticks
            await asyncio.sleep(1)

        # Show final statistics
        await self.show_statistics()

    async def monitor_live_prices(self):
        """Monitor actual live price data"""
        logger.info("🔍 Monitoring live SPX prices...")

        while self.monitoring:
            try:
                # Get latest price from database
                cursor = await self.conn.execute("""
                    SELECT price, timestamp
                    FROM spx_price_ticks
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                row = await cursor.fetchone()

                if row:
                    price, timestamp = row

                    # Only process if price changed
                    if price != self.last_price:
                        logger.info(f"\n📊 SPX: ${price:.2f}")

                        # Process through level detector
                        hits = await self.detector.process_price_tick(price, timestamp)

                        for hit in hits:
                            logger.info(f"🎯 LEVEL HIT: {hit['level_name']} [{hit['timeframe']}]")

                            # Process through movement tracker
                            movement = await self.tracker.process_new_hit(hit)

                            if movement:
                                logger.info(
                                    f"🔗 MOVEMENT: {movement.from_level} → {movement.to_level} | "
                                    f"Duration: {movement.duration_seconds:.1f}s | "
                                    f"Direction: {movement.direction}"
                                )

                                if movement.pattern_type:
                                    logger.info(f"🌟 PATTERN: {movement.pattern_type}")

                        self.last_price = price

                await asyncio.sleep(5)  # Check every 5 seconds

            except KeyboardInterrupt:
                self.monitoring = False
                break
            except Exception as e:
                logger.error(f"Error in monitoring: {e}")
                await asyncio.sleep(5)

    async def show_statistics(self):
        """Display movement statistics"""
        logger.info("\n" + "="*80)
        logger.info("📊 MOVEMENT STATISTICS")
        logger.info("="*80)

        # Get hit statistics
        hit_stats = await self.detector.get_hit_statistics()
        logger.info(f"\nTotal Level Hits Today: {hit_stats.get('total_hits_today', 0)}")
        logger.info(f"Hits by Timeframe: {hit_stats.get('hits_by_timeframe', {})}")

        # Get transition statistics
        transition_stats = await self.tracker.calculate_transition_stats()
        if transition_stats.get('transitions'):
            logger.info(f"\nTotal Transitions: {transition_stats['total_transitions']}")
            logger.info("\nTop Transitions:")
            for trans in transition_stats['transitions'][:10]:
                logger.info(
                    f"  {trans['from']:15} → {trans['to']:15} | "
                    f"Count: {trans['count']} | "
                    f"Avg Duration: {trans['avg_duration']:.1f}s"
                )

        # Get active chains
        chains = await self.tracker.get_active_chains_summary()
        if chains:
            logger.info("\nActive Movement Chains:")
            for tf, chain in chains.items():
                logger.info(f"\n  {tf}:")
                logger.info(f"    Current: {chain['start_level']} → {chain['current_level']}")
                logger.info(f"    Movements: {chain['movements_count']}")
                logger.info(f"    Levels Traversed: {chain['total_levels_traversed']}")
                if chain['pattern_detected']:
                    logger.info(f"    Pattern: {chain['pattern_detected']}")

    async def show_movement_predictions(self, current_price: float):
        """Show likely next movements based on current position"""
        logger.info("\n" + "="*80)
        logger.info("🔮 MOVEMENT PREDICTIONS")
        logger.info("="*80)

        for timeframe in ['5m', '15m', '30m', '1h']:
            position = self.detector.calculator.get_price_position(current_price, timeframe)
            if position:
                logger.info(f"\n{timeframe}:")
                logger.info(f"  Current Zone: {position['current_zone']}")

                if position['nearest_above']:
                    next_up = position['nearest_above'][0]
                    logger.info(f"  🎯 Next Target Up: {next_up['name']} @ ${next_up['value']:.2f} "
                              f"(${next_up['distance']:.2f} away)")

                if position['nearest_below']:
                    next_down = position['nearest_below'][0]
                    logger.info(f"  🎯 Next Target Down: {next_down['name']} @ ${next_down['value']:.2f} "
                              f"(${next_down['distance']:.2f} away)")

                # Check for potential patterns
                current_level = None
                for level_name, level in self.detector.calculator.levels_cache[timeframe]['levels'].items():
                    if abs(current_price - level.value) < 1.0:
                        current_level = level_name
                        break

                if current_level:
                    # Predict potential patterns
                    if current_level == 'upper_0382':
                        logger.info(f"  ⚡ Potential Pattern: Golden Gate Bull if reaches upper_0618")
                    elif current_level == 'lower_0382':
                        logger.info(f"  ⚡ Potential Pattern: Golden Gate Bear if reaches lower_0618")
                    elif current_level == 'PDC':
                        logger.info(f"  ⚡ Potential Patterns: Trigger breakout/breakdown at ±23.6%")

    async def close(self):
        """Clean up resources"""
        await self.detector.close()
        await self.tracker.close()
        if self.conn:
            await self.conn.close()


async def main():
    """Main function"""
    monitor = RealtimeMovementMonitor()
    await monitor.initialize()

    # Check current price
    conn = await aiosqlite.connect(DB_PATH)
    cursor = await conn.execute("""
        SELECT price FROM spx_price_ticks
        ORDER BY timestamp DESC LIMIT 1
    """)
    row = await cursor.fetchone()
    current_price = row[0] if row else 6664.36
    await conn.close()

    logger.info(f"\n🎯 Current SPX Price: ${current_price:.2f}")

    # Show movement predictions
    await monitor.show_movement_predictions(current_price)

    # Choose mode
    print("\n" + "="*60)
    print("SELECT MODE:")
    print("1. Simulate price movements (test pattern detection)")
    print("2. Monitor live prices")
    print("3. Show statistics only")
    print("="*60)

    choice = input("Enter choice (1-3): ").strip()

    if choice == '1':
        await monitor.simulate_price_movements()
    elif choice == '2':
        await monitor.monitor_live_prices()
    else:
        await monitor.show_statistics()

    await monitor.close()


if __name__ == "__main__":
    asyncio.run(main())