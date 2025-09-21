#!/usr/bin/env python3
"""
Real-time Level Hit Detection and Storage
Monitors live SPX prices and detects/stores all level crosses
"""
import asyncio
import aiosqlite
import logging
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
import json
import os

from comprehensive_level_detector import ComprehensiveLevelCalculator, ATRLevel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = Path(os.getenv("DB_PATH", "./data/whispr.db"))

class RealtimeLevelHitDetector:
    """Detects and stores level hits in real-time"""

    TIMEFRAMES = ['5m', '15m', '30m', '1h', '2h', '4h', 'daily', 'weekly']

    def __init__(self):
        self.calculator = ComprehensiveLevelCalculator()
        self.previous_prices = {}  # Store previous price for each timeframe
        self.conn = None
        self.current_atr_data = {}  # Cache current ATR values
        self.session_date = date.today().isoformat()

    async def initialize(self):
        """Initialize database connection and load ATR data"""
        self.conn = await aiosqlite.connect(DB_PATH)
        await self.load_current_atr_data()
        logger.info("✅ Level hit detector initialized")

    async def load_current_atr_data(self):
        """Load current ATR levels from database"""
        try:
            cursor = await self.conn.execute("""
                SELECT timeframe, atr_value, previous_close
                FROM atr_levels
                WHERE session_date = ?
            """, (self.session_date,))

            rows = await cursor.fetchall()
            for row in rows:
                timeframe, atr_value, previous_close = row
                self.current_atr_data[timeframe] = {
                    'atr': atr_value,
                    'pdc': previous_close
                }

                # Calculate all 28 levels for this timeframe
                if atr_value and previous_close:
                    levels = self.calculator.calculate_all_levels(
                        pdc=previous_close,
                        atr_value=atr_value,
                        timeframe=timeframe
                    )
                    logger.info(f"📊 Loaded {len(levels)} levels for {timeframe}: PDC=${previous_close:.2f}, ATR=${atr_value:.2f}")

        except Exception as e:
            logger.error(f"Error loading ATR data: {e}")

    async def process_price_tick(self, price: float, timestamp: str) -> List[Dict]:
        """
        Process a new price tick and detect level crosses
        Returns list of detected level hits
        """
        all_hits = []

        for timeframe in self.TIMEFRAMES:
            if timeframe not in self.current_atr_data:
                continue

            # Get ATR data for this timeframe
            atr_data = self.current_atr_data[timeframe]
            if not atr_data.get('atr') or not atr_data.get('pdc'):
                continue

            # Get or calculate levels
            if timeframe not in self.calculator.levels_cache:
                self.calculator.calculate_all_levels(
                    pdc=atr_data['pdc'],
                    atr_value=atr_data['atr'],
                    timeframe=timeframe
                )

            levels = self.calculator.levels_cache[timeframe]['levels']

            # Check for level crosses if we have a previous price
            if timeframe in self.previous_prices:
                crosses = self.calculator.detect_level_crosses(
                    current_price=price,
                    previous_price=self.previous_prices[timeframe],
                    levels=levels,
                    timeframe=timeframe
                )

                for cross in crosses:
                    # Store in database
                    hit_id = await self.store_level_hit(cross, atr_data['pdc'], atr_data['atr'])
                    cross['hit_id'] = hit_id
                    all_hits.append(cross)

                    # Log the hit
                    logger.info(
                        f"🎯 LEVEL HIT [{timeframe}]: {cross['level_name']} "
                        f"@ ${cross['level_value']:.2f} | Price: ${price:.2f} | "
                        f"Direction: {cross['cross_direction']}"
                    )

            # Update previous price for this timeframe
            self.previous_prices[timeframe] = price

        return all_hits

    async def store_level_hit(self, hit_data: Dict, pdc: float, atr: float) -> int:
        """Store level hit in database"""
        try:
            cursor = await self.conn.execute("""
                INSERT INTO level_hits
                (hit_time, timeframe, level_name, level_value, hit_price,
                 direction, fib_ratio, previous_close, atr_value, session_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                hit_data['timestamp'],
                hit_data['timeframe'],
                hit_data['level_name'],
                hit_data['level_value'],
                hit_data['price_at_cross'],
                hit_data['cross_direction'],
                hit_data['fib_ratio'],
                pdc,
                atr,
                self.session_date
            ))
            await self.conn.commit()
            return cursor.lastrowid

        except Exception as e:
            logger.error(f"Error storing level hit: {e}")
            return None

    async def get_current_position_analysis(self, current_price: float) -> Dict:
        """Get comprehensive position analysis across all timeframes"""
        analysis = {
            'current_price': current_price,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'timeframes': {}
        }

        for timeframe in self.TIMEFRAMES:
            if timeframe in self.calculator.levels_cache:
                position = self.calculator.get_price_position(current_price, timeframe)
                if position:
                    analysis['timeframes'][timeframe] = position

        return analysis

    async def get_recent_hits(self, limit: int = 20) -> List[Dict]:
        """Get recent level hits from database"""
        try:
            cursor = await self.conn.execute("""
                SELECT hit_time, timeframe, level_name, level_value,
                       hit_price, direction, fib_ratio
                FROM level_hits
                WHERE session_date = ?
                ORDER BY hit_time DESC
                LIMIT ?
            """, (self.session_date, limit))

            rows = await cursor.fetchall()
            hits = []
            for row in rows:
                hits.append({
                    'hit_time': row[0],
                    'timeframe': row[1],
                    'level_name': row[2],
                    'level_value': row[3],
                    'hit_price': row[4],
                    'direction': row[5],
                    'fib_ratio': row[6]
                })
            return hits

        except Exception as e:
            logger.error(f"Error getting recent hits: {e}")
            return []

    async def get_hit_statistics(self) -> Dict:
        """Get statistics on level hits"""
        try:
            # Total hits today
            cursor = await self.conn.execute("""
                SELECT COUNT(*) FROM level_hits
                WHERE session_date = ?
            """, (self.session_date,))
            total_hits = (await cursor.fetchone())[0]

            # Hits by timeframe
            cursor = await self.conn.execute("""
                SELECT timeframe, COUNT(*)
                FROM level_hits
                WHERE session_date = ?
                GROUP BY timeframe
            """, (self.session_date,))
            hits_by_timeframe = dict(await cursor.fetchall())

            # Most hit levels
            cursor = await self.conn.execute("""
                SELECT level_name, COUNT(*) as hit_count
                FROM level_hits
                WHERE session_date = ?
                GROUP BY level_name
                ORDER BY hit_count DESC
                LIMIT 10
            """, (self.session_date,))
            most_hit_levels = await cursor.fetchall()

            return {
                'total_hits_today': total_hits,
                'hits_by_timeframe': hits_by_timeframe,
                'most_hit_levels': most_hit_levels,
                'session_date': self.session_date
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

    def display_all_levels(self, current_price: float):
        """Display all levels for all timeframes"""
        for timeframe in self.TIMEFRAMES:
            if timeframe in self.calculator.levels_cache:
                print(self.calculator.format_level_display(current_price, timeframe))

    async def close(self):
        """Clean up resources"""
        if self.conn:
            await self.conn.close()


async def main():
    """Test the level detector with current data"""
    detector = RealtimeLevelHitDetector()
    await detector.initialize()

    # Get current SPX price from database
    conn = await aiosqlite.connect(DB_PATH)
    cursor = await conn.execute("""
        SELECT price, timestamp FROM spx_price_ticks
        ORDER BY timestamp DESC LIMIT 1
    """)
    row = await cursor.fetchone()

    if row:
        current_price, timestamp = row
        logger.info(f"\n📈 Current SPX: ${current_price:.2f} @ {timestamp}")

        # Process the price tick
        hits = await detector.process_price_tick(current_price, timestamp)

        # Display all levels
        detector.display_all_levels(current_price)

        # Get position analysis
        analysis = await detector.get_current_position_analysis(current_price)
        print("\n🎯 POSITION ANALYSIS:")
        for tf, data in analysis['timeframes'].items():
            print(f"\n{tf}:")
            print(f"  Zone: {data['current_zone']}")
            print(f"  ATR Multiple: {data['atr_multiple']}")
            print(f"  % from PDC: {data['percentage_from_pdc']}%")
            if data['nearest_above']:
                print(f"  Next Level Up: {data['nearest_above'][0]['name']} @ ${data['nearest_above'][0]['value']:.2f} (${data['nearest_above'][0]['distance']:.2f} away)")
            if data['nearest_below']:
                print(f"  Next Level Down: {data['nearest_below'][0]['name']} @ ${data['nearest_below'][0]['value']:.2f} (${data['nearest_below'][0]['distance']:.2f} away)")

        # Get statistics
        stats = await detector.get_hit_statistics()
        print(f"\n📊 STATISTICS:")
        print(f"  Total Hits Today: {stats.get('total_hits_today', 0)}")
        print(f"  Hits by Timeframe: {stats.get('hits_by_timeframe', {})}")

    await conn.close()
    await detector.close()


if __name__ == "__main__":
    asyncio.run(main())