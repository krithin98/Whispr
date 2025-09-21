#!/usr/bin/env python3
"""
Level-to-Level Movement Tracking System
Links consecutive level hits into movement chains and analyzes patterns
"""
import asyncio
import aiosqlite
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json
from pathlib import Path
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DB_PATH = Path(os.getenv("DB_PATH", "./data/whispr.db"))

@dataclass
class LevelMovement:
    """Represents a single level-to-level movement"""
    from_level: str
    to_level: str
    from_hit_id: int
    to_hit_id: int
    timeframe: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    price_start: float
    price_end: float
    price_change: float
    direction: str  # 'bullish', 'bearish', 'neutral'
    levels_traversed: int
    velocity: float  # levels per minute
    pattern_type: Optional[str] = None  # e.g., 'golden_gate', 'breakdown', etc.

@dataclass
class MovementChain:
    """Represents a chain of connected movements"""
    chain_id: str
    timeframe: str
    movements: List[LevelMovement] = field(default_factory=list)
    start_level: str = None
    current_level: str = None
    total_duration: float = 0
    total_levels_traversed: int = 0
    chain_direction: str = None  # Overall direction
    pattern_detected: Optional[str] = None

class MovementTracker:
    """Tracks and analyzes level-to-level movements"""

    # Define level order for calculating traversal distance
    LEVEL_ORDER = [
        'beyond_minus2atr', 'lower_2000', 'lower_1786', 'lower_1618', 'lower_1500',
        'lower_1382', 'lower_1236', 'lower_1000', 'lower_0786', 'lower_0618',
        'lower_0500', 'lower_0382', 'lower_trigger',
        'PDC',  # Center reference
        'upper_trigger', 'upper_0382', 'upper_0500', 'upper_0618', 'upper_0786',
        'upper_1000', 'upper_1236', 'upper_1382', 'upper_1500', 'upper_1618',
        'upper_1786', 'upper_2000', 'beyond_2atr'
    ]

    # Define notable patterns
    PATTERNS = {
        'golden_gate_bull': ['upper_0382', 'upper_0618'],
        'golden_gate_bear': ['lower_0382', 'lower_0618'],
        'full_atr_bull': ['PDC', 'upper_1000'],
        'full_atr_bear': ['PDC', 'lower_1000'],
        'trigger_breakout': ['PDC', 'upper_trigger'],
        'trigger_breakdown': ['PDC', 'lower_trigger'],
        'double_atr_extension': ['upper_1000', 'upper_2000'],
        'double_atr_collapse': ['lower_1000', 'lower_2000']
    }

    def __init__(self):
        self.conn = None
        self.active_chains = {}  # Track active movement chains per timeframe
        self.last_hits = {}  # Track last hit per timeframe for linking

    async def initialize(self):
        """Initialize database connection"""
        self.conn = await aiosqlite.connect(DB_PATH)
        await self.load_recent_hits()
        logger.info("✅ Movement tracker initialized")

    async def load_recent_hits(self):
        """Load most recent hits for each timeframe to establish starting point"""
        try:
            cursor = await self.conn.execute("""
                SELECT DISTINCT timeframe FROM level_hits
                WHERE session_date = DATE('now')
            """)
            timeframes = [row[0] for row in await cursor.fetchall()]

            for tf in timeframes:
                cursor = await self.conn.execute("""
                    SELECT id, level_name, hit_price, hit_time
                    FROM level_hits
                    WHERE timeframe = ? AND session_date = DATE('now')
                    ORDER BY hit_time DESC
                    LIMIT 1
                """, (tf,))

                row = await cursor.fetchone()
                if row:
                    self.last_hits[tf] = {
                        'hit_id': row[0],
                        'level': row[1],
                        'price': row[2],
                        'time': datetime.fromisoformat(row[3])
                    }
                    logger.info(f"📍 Last hit for {tf}: {row[1]} @ ${row[2]:.2f}")

        except Exception as e:
            logger.error(f"Error loading recent hits: {e}")

    def get_level_index(self, level_name: str) -> int:
        """Get the index position of a level"""
        try:
            return self.LEVEL_ORDER.index(level_name)
        except ValueError:
            return -1

    def calculate_levels_traversed(self, from_level: str, to_level: str) -> int:
        """Calculate how many levels were traversed"""
        from_idx = self.get_level_index(from_level)
        to_idx = self.get_level_index(to_level)

        if from_idx == -1 or to_idx == -1:
            return 0

        return abs(to_idx - from_idx)

    def determine_direction(self, from_level: str, to_level: str) -> str:
        """Determine movement direction"""
        from_idx = self.get_level_index(from_level)
        to_idx = self.get_level_index(to_level)

        if from_idx == -1 or to_idx == -1:
            return 'unknown'
        elif to_idx > from_idx:
            return 'bullish'
        elif to_idx < from_idx:
            return 'bearish'
        else:
            return 'neutral'

    def detect_pattern(self, movements: List[LevelMovement]) -> Optional[str]:
        """Detect if movements match a known pattern"""
        if not movements:
            return None

        # Check recent movements for patterns
        recent_levels = [m.from_level for m in movements[-3:]]
        recent_levels.append(movements[-1].to_level)

        for pattern_name, pattern_levels in self.PATTERNS.items():
            # Check if recent levels contain the pattern
            if all(level in recent_levels for level in pattern_levels):
                # Verify sequence order
                indices = [recent_levels.index(level) for level in pattern_levels]
                if indices == sorted(indices):
                    return pattern_name

        return None

    async def process_new_hit(self, hit_data: Dict) -> Optional[LevelMovement]:
        """Process a new level hit and link it to previous hits"""
        timeframe = hit_data['timeframe']

        # Check if we have a previous hit to link to
        if timeframe not in self.last_hits:
            # First hit for this timeframe
            self.last_hits[timeframe] = {
                'hit_id': hit_data['hit_id'],
                'level': hit_data['level_name'],
                'price': hit_data['price_at_cross'],
                'time': datetime.fromisoformat(hit_data['timestamp'])
            }
            logger.info(f"🆕 First hit for {timeframe}: {hit_data['level_name']}")
            return None

        # Create movement from previous to current
        prev = self.last_hits[timeframe]

        # Calculate movement metrics
        duration = (datetime.fromisoformat(hit_data['timestamp']) - prev['time']).total_seconds()
        if duration <= 0:
            duration = 1  # Minimum 1 second

        levels_traversed = self.calculate_levels_traversed(prev['level'], hit_data['level_name'])
        velocity = (levels_traversed / duration) * 60 if duration > 0 else 0  # Levels per minute

        movement = LevelMovement(
            from_level=prev['level'],
            to_level=hit_data['level_name'],
            from_hit_id=prev['hit_id'],
            to_hit_id=hit_data['hit_id'],
            timeframe=timeframe,
            start_time=prev['time'],
            end_time=datetime.fromisoformat(hit_data['timestamp']),
            duration_seconds=duration,
            price_start=prev['price'],
            price_end=hit_data['price_at_cross'],
            price_change=hit_data['price_at_cross'] - prev['price'],
            direction=self.determine_direction(prev['level'], hit_data['level_name']),
            levels_traversed=levels_traversed,
            velocity=velocity
        )

        # Update the link in database
        await self.update_hit_link(prev['hit_id'], hit_data['hit_id'])

        # Update last hit
        self.last_hits[timeframe] = {
            'hit_id': hit_data['hit_id'],
            'level': hit_data['level_name'],
            'price': hit_data['price_at_cross'],
            'time': datetime.fromisoformat(hit_data['timestamp'])
        }

        # Add to active chain
        await self.add_to_chain(movement)

        return movement

    async def update_hit_link(self, from_hit_id: int, to_hit_id: int):
        """Update the next_level_hit_id link in database"""
        try:
            await self.conn.execute("""
                UPDATE level_hits
                SET next_level_hit_id = ?
                WHERE id = ?
            """, (to_hit_id, from_hit_id))
            await self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating hit link: {e}")

    async def add_to_chain(self, movement: LevelMovement):
        """Add movement to active chain and detect patterns"""
        tf = movement.timeframe

        if tf not in self.active_chains:
            # Start new chain
            chain_id = f"{tf}_{datetime.now(timezone.utc).isoformat()}"
            self.active_chains[tf] = MovementChain(
                chain_id=chain_id,
                timeframe=tf,
                start_level=movement.from_level
            )

        chain = self.active_chains[tf]
        chain.movements.append(movement)
        chain.current_level = movement.to_level
        chain.total_duration += movement.duration_seconds
        chain.total_levels_traversed += movement.levels_traversed

        # Detect pattern
        pattern = self.detect_pattern(chain.movements)
        if pattern and pattern != chain.pattern_detected:
            chain.pattern_detected = pattern
            movement.pattern_type = pattern
            logger.info(f"🎯 PATTERN DETECTED [{tf}]: {pattern}")
            await self.store_pattern_detection(movement, pattern)

        # Log movement
        logger.info(
            f"🔗 MOVEMENT [{tf}]: {movement.from_level} → {movement.to_level} | "
            f"Duration: {movement.duration_seconds:.1f}s | "
            f"Velocity: {movement.velocity:.2f} levels/min | "
            f"Direction: {movement.direction}"
        )

    async def store_pattern_detection(self, movement: LevelMovement, pattern: str):
        """Store detected pattern in database"""
        try:
            await self.conn.execute("""
                INSERT INTO movement_patterns
                (detection_time, timeframe, pattern_type, from_level, to_level,
                 from_hit_id, to_hit_id, duration_seconds, price_change)
                VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                movement.timeframe, pattern, movement.from_level, movement.to_level,
                movement.from_hit_id, movement.to_hit_id, movement.duration_seconds,
                movement.price_change
            ))
            await self.conn.commit()
        except Exception as e:
            logger.error(f"Error storing pattern: {e}")

    async def calculate_transition_stats(self, timeframe: str = None) -> Dict:
        """Calculate statistics for level transitions"""
        try:
            where_clause = "WHERE 1=1"
            params = []

            if timeframe:
                where_clause += " AND h1.timeframe = ?"
                params.append(timeframe)

            query = f"""
                SELECT
                    h1.level_name as from_level,
                    h2.level_name as to_level,
                    COUNT(*) as transition_count,
                    AVG((julianday(h2.hit_time) - julianday(h1.hit_time)) * 86400) as avg_duration_seconds,
                    MIN((julianday(h2.hit_time) - julianday(h1.hit_time)) * 86400) as min_duration,
                    MAX((julianday(h2.hit_time) - julianday(h1.hit_time)) * 86400) as max_duration,
                    AVG(h2.hit_price - h1.hit_price) as avg_price_change
                FROM level_hits h1
                JOIN level_hits h2 ON h1.next_level_hit_id = h2.id
                {where_clause}
                GROUP BY h1.level_name, h2.level_name
                ORDER BY transition_count DESC
            """

            cursor = await self.conn.execute(query, params)
            rows = await cursor.fetchall()

            stats = {
                'transitions': [],
                'total_transitions': 0
            }

            for row in rows:
                stats['transitions'].append({
                    'from': row[0],
                    'to': row[1],
                    'count': row[2],
                    'avg_duration': row[3],
                    'min_duration': row[4],
                    'max_duration': row[5],
                    'avg_price_change': row[6]
                })
                stats['total_transitions'] += row[2]

            return stats

        except Exception as e:
            logger.error(f"Error calculating transition stats: {e}")
            return {}

    async def get_active_chains_summary(self) -> Dict:
        """Get summary of all active movement chains"""
        summary = {}

        for tf, chain in self.active_chains.items():
            summary[tf] = {
                'chain_id': chain.chain_id,
                'start_level': chain.start_level,
                'current_level': chain.current_level,
                'movements_count': len(chain.movements),
                'total_duration': chain.total_duration,
                'total_levels_traversed': chain.total_levels_traversed,
                'pattern_detected': chain.pattern_detected,
                'last_movement': None
            }

            if chain.movements:
                last = chain.movements[-1]
                summary[tf]['last_movement'] = {
                    'from': last.from_level,
                    'to': last.to_level,
                    'duration': last.duration_seconds,
                    'velocity': last.velocity,
                    'direction': last.direction
                }

        return summary

    async def close(self):
        """Clean up resources"""
        if self.conn:
            await self.conn.close()