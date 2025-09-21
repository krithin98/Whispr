#!/usr/bin/env python3
"""
Comprehensive ATR Level Detection System
Detects all 28 ATR levels across all timeframes in real-time
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class ATRLevel:
    """Represents a single ATR level"""
    name: str
    fib_ratio: float  # Percentage from PDC (0% = PDC)
    value: float
    direction: str  # 'upper', 'lower', or 'neutral'

class ComprehensiveLevelCalculator:
    """Calculate all 28 ATR levels for any timeframe"""

    # Define all 28 levels with their Fibonacci ratios
    LEVEL_DEFINITIONS = [
        # Upper/Bullish levels (above PDC)
        ("upper_trigger", 0.236, "upper"),
        ("upper_0382", 0.382, "upper"),
        ("upper_0500", 0.500, "upper"),
        ("upper_0618", 0.618, "upper"),
        ("upper_0786", 0.786, "upper"),
        ("upper_1000", 1.000, "upper"),  # +1 ATR
        ("upper_1236", 1.236, "upper"),
        ("upper_1382", 1.382, "upper"),
        ("upper_1500", 1.500, "upper"),
        ("upper_1618", 1.618, "upper"),
        ("upper_1786", 1.786, "upper"),
        ("upper_2000", 2.000, "upper"),  # +2 ATR
        ("beyond_2atr", 2.001, "upper"),  # Tracking beyond +2 ATR

        # Neutral level (PDC = 0%)
        ("PDC", 0.000, "neutral"),  # Previous Day Close - the true zero

        # Lower/Bearish levels (below PDC)
        ("lower_trigger", -0.236, "lower"),
        ("lower_0382", -0.382, "lower"),
        ("lower_0500", -0.500, "lower"),
        ("lower_0618", -0.618, "lower"),
        ("lower_0786", -0.786, "lower"),
        ("lower_1000", -1.000, "lower"),  # -1 ATR
        ("lower_1236", -1.236, "lower"),
        ("lower_1382", -1.382, "lower"),
        ("lower_1500", -1.500, "lower"),
        ("lower_1618", -1.618, "lower"),
        ("lower_1786", -1.786, "lower"),
        ("lower_2000", -2.000, "lower"),  # -2 ATR
        ("beyond_minus2atr", -2.001, "lower"),  # Tracking beyond -2 ATR
    ]

    def __init__(self):
        self.levels_cache = {}
        self.last_hit_levels = {}  # Track last hit level per timeframe

    def calculate_all_levels(self, pdc: float, atr_value: float, timeframe: str) -> Dict[str, ATRLevel]:
        """
        Calculate all 28 ATR levels
        PDC is the 0% reference point
        """
        levels = {}

        for name, fib_ratio, direction in self.LEVEL_DEFINITIONS:
            if name == "PDC":
                value = pdc
            else:
                # Calculate level value: PDC ± (ATR * fib_ratio)
                value = pdc + (atr_value * fib_ratio)

            levels[name] = ATRLevel(
                name=name,
                fib_ratio=fib_ratio,
                value=value,
                direction=direction
            )

        # Cache the calculated levels
        self.levels_cache[timeframe] = {
            'pdc': pdc,
            'atr': atr_value,
            'levels': levels,
            'calculated_at': datetime.now(timezone.utc).isoformat()
        }

        return levels

    def detect_level_crosses(self, current_price: float, previous_price: float,
                           levels: Dict[str, ATRLevel], timeframe: str) -> List[Dict]:
        """
        Detect which levels were crossed between previous and current price
        Returns list of crossed levels with details
        """
        crossed = []

        for name, level in levels.items():
            # Skip beyond tracking levels for crossing detection
            if 'beyond' in name:
                continue

            # Check if price crossed this level
            if previous_price <= level.value < current_price:
                # Crossed upward through level
                crossed.append({
                    'timeframe': timeframe,
                    'level_name': name,
                    'level_value': level.value,
                    'cross_direction': 'up',
                    'fib_ratio': level.fib_ratio,
                    'price_at_cross': current_price,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            elif previous_price >= level.value > current_price:
                # Crossed downward through level
                crossed.append({
                    'timeframe': timeframe,
                    'level_name': name,
                    'level_value': level.value,
                    'cross_direction': 'down',
                    'fib_ratio': level.fib_ratio,
                    'price_at_cross': current_price,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })

        # Check if price is beyond ±2 ATR
        pdc = self.levels_cache[timeframe]['pdc']
        atr = self.levels_cache[timeframe]['atr']

        if current_price > pdc + (2 * atr):
            crossed.append({
                'timeframe': timeframe,
                'level_name': 'beyond_2atr',
                'level_value': pdc + (2 * atr),
                'cross_direction': 'beyond_upper',
                'fib_ratio': (current_price - pdc) / atr,  # Show how many ATRs away
                'price_at_cross': current_price,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        elif current_price < pdc - (2 * atr):
            crossed.append({
                'timeframe': timeframe,
                'level_name': 'beyond_minus2atr',
                'level_value': pdc - (2 * atr),
                'cross_direction': 'beyond_lower',
                'fib_ratio': (current_price - pdc) / atr,  # Show how many ATRs away (negative)
                'price_at_cross': current_price,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

        return crossed

    def find_nearest_levels(self, current_price: float, levels: Dict[str, ATRLevel],
                           count: int = 3) -> Tuple[List[ATRLevel], List[ATRLevel]]:
        """
        Find the nearest levels above and below current price
        """
        above = []
        below = []

        for name, level in levels.items():
            if 'beyond' in name:
                continue

            if level.value > current_price:
                above.append(level)
            elif level.value < current_price:
                below.append(level)

        # Sort and get nearest
        above.sort(key=lambda x: x.value)
        below.sort(key=lambda x: x.value, reverse=True)

        return above[:count], below[:count]

    def get_price_position(self, current_price: float, timeframe: str) -> Dict:
        """
        Get comprehensive position analysis for current price
        """
        if timeframe not in self.levels_cache:
            return None

        cache = self.levels_cache[timeframe]
        pdc = cache['pdc']
        atr = cache['atr']
        levels = cache['levels']

        # Calculate position metrics
        distance_from_pdc = current_price - pdc
        atr_multiple = distance_from_pdc / atr if atr > 0 else 0
        percentage_from_pdc = (distance_from_pdc / pdc) * 100 if pdc > 0 else 0

        # Find nearest levels
        above_levels, below_levels = self.find_nearest_levels(current_price, levels, count=3)

        # Determine current zone
        current_zone = "neutral"
        if atr_multiple > 2.0:
            current_zone = "beyond_+2ATR"
        elif atr_multiple > 1.0:
            current_zone = "between_+1ATR_and_+2ATR"
        elif atr_multiple > 0:
            current_zone = "between_PDC_and_+1ATR"
        elif atr_multiple > -1.0:
            current_zone = "between_PDC_and_-1ATR"
        elif atr_multiple > -2.0:
            current_zone = "between_-1ATR_and_-2ATR"
        else:
            current_zone = "beyond_-2ATR"

        return {
            'timeframe': timeframe,
            'current_price': current_price,
            'pdc': pdc,
            'atr': atr,
            'distance_from_pdc': distance_from_pdc,
            'atr_multiple': round(atr_multiple, 3),
            'percentage_from_pdc': round(percentage_from_pdc, 2),
            'current_zone': current_zone,
            'nearest_above': [{'name': l.name, 'value': l.value, 'distance': l.value - current_price}
                             for l in above_levels],
            'nearest_below': [{'name': l.name, 'value': l.value, 'distance': current_price - l.value}
                             for l in below_levels],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def format_level_display(self, current_price: float, timeframe: str) -> str:
        """
        Format a nice display of all levels with current price position
        """
        if timeframe not in self.levels_cache:
            return f"No levels calculated for {timeframe}"

        cache = self.levels_cache[timeframe]
        pdc = cache['pdc']
        atr = cache['atr']
        levels = cache['levels']

        lines = []
        lines.append(f"\n{'='*70}")
        lines.append(f"ATR LEVELS for {timeframe} | PDC: ${pdc:.2f} | ATR: ${atr:.2f}")
        lines.append(f"Current Price: ${current_price:.2f}")
        lines.append(f"{'='*70}")

        # Sort levels by value descending
        sorted_levels = sorted(levels.values(), key=lambda x: x.value, reverse=True)

        for level in sorted_levels:
            if 'beyond' in level.name:
                continue

            # Determine position indicator
            if abs(current_price - level.value) < 0.50:
                indicator = " <<<--- CURRENT PRICE HERE"
            elif current_price > level.value:
                indicator = " ✓"  # Price is above this level
            else:
                indicator = ""  # Price is below this level

            # Special formatting for key levels
            if level.name == "PDC":
                lines.append(f"{'─'*70}")
                lines.append(f"  {level.name:15} | ${level.value:8.2f} | {level.fib_ratio:+6.1%} | *** ZERO REFERENCE ***{indicator}")
                lines.append(f"{'─'*70}")
            elif abs(level.fib_ratio) == 1.0:
                lines.append(f"  {level.name:15} | ${level.value:8.2f} | {level.fib_ratio:+6.1%} | {'='*10}{indicator}")
            elif abs(level.fib_ratio) == 2.0:
                lines.append(f"  {level.name:15} | ${level.value:8.2f} | {level.fib_ratio:+6.1%} | {'='*20}{indicator}")
            else:
                lines.append(f"  {level.name:15} | ${level.value:8.2f} | {level.fib_ratio:+6.1%}{indicator}")

        # Add position summary
        distance = current_price - pdc
        atr_multiple = distance / atr if atr > 0 else 0
        lines.append(f"\n{'─'*70}")
        lines.append(f"Position: {atr_multiple:+.3f} ATR from PDC (${distance:+.2f})")
        lines.append(f"{'='*70}\n")

        return '\n'.join(lines)