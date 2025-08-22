#!/usr/bin/env python3
"""
ATR System - Integration & Orchestration Layer
Coordinates data collection, ATR calculations, and level tracking for SPX.
This is the main conductor that brings all ATR components together.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass

# Import our modular components
from data_collector import SchwabDataCollector, MarketTick, OHLCCandle, get_data_collector
from atr_calculator import ATRCalculator, ATRLevels
from fixed_fib_level_strategy import FixedFibonacciLevelTracker, FibLevelHit
from timeframe_aggregator import SPXTimeframeAggregator, OHLCBar
from database import (
    log_event, log_spx_tick, store_atr_levels, log_level_hit,
    start_golden_gate_sequence, complete_golden_gate_sequence,
    update_daily_session_summary
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ATRSystemState:
    """Current state of the ATR system"""
    current_price: float
    last_update: datetime
    active_levels: Dict[str, ATRLevels]  # timeframe -> levels
    recent_hits: List[FibLevelHit]
    system_status: str

class SPXATRSystem:
    """
    Main ATR System for SPX level tracking.
    Orchestrates data collection, timeframe aggregation, ATR calculations, and level tracking.
    """
    
    def __init__(self):
        self.data_collector: Optional[SchwabDataCollector] = None
        self.timeframe_aggregator = SPXTimeframeAggregator()
        self.fib_tracker = FixedFibonacciLevelTracker()
        
        # System state
        self.state = ATRSystemState(
            current_price=0.0,
            last_update=datetime.now(timezone.utc),
            active_levels={},
            recent_hits=[],
            system_status="stopped"
        )
        
        # Performance tracking
        self.stats = {
            "total_ticks_processed": 0,
            "level_hits_detected": 0,
            "last_calculation_time": None,
            "avg_processing_time_ms": 0.0
        }
        
        logger.info("🎯 SPX ATR System initialized")
    
    async def initialize(self) -> bool:
        """Initialize all system components"""
        try:
            logger.info("🚀 Initializing SPX ATR System...")
            
            # Initialize data collector
            self.data_collector = await get_data_collector()
            if not self.data_collector.connected:
                logger.error("❌ Data collector not connected")
                return False
            
            # Fibonacci tracker is already initialized in constructor
            
            self.state.system_status = "initialized"
            logger.info("✅ SPX ATR System ready")
            
            await log_event("atr_system_initialized", {
                "timestamp": datetime.now().isoformat(),
                "components": ["data_collector", "timeframe_aggregator", "fib_tracker"]
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize ATR system: {e}")
            self.state.system_status = "error"
            return False
    
    async def process_market_tick(self, tick: MarketTick) -> List[FibLevelHit]:
        """
        Process a single market tick through the entire ATR pipeline.
        This is the core processing function.
        """
        start_time = datetime.now()
        hits = []
        
        try:
            # Update system state
            self.state.current_price = tick.price
            self.state.last_update = tick.timestamp
            self.stats["total_ticks_processed"] += 1
            
            # Store tick data in database
            try:
                await log_spx_tick(
                    price=tick.price,
                    high=tick.high,
                    low=tick.low,
                    volume=getattr(tick, 'volume', 0),
                    timestamp=tick.timestamp.isoformat()
                )
            except Exception as e:
                logger.debug(f"Failed to store tick data: {e}")  # Debug level since this happens frequently
            
            # 1. Feed tick to timeframe aggregator
            self.timeframe_aggregator.add_tick_data(
                tick.timestamp, tick.price, tick.high, tick.low
            )
            
            # Get updated aggregated data
            aggregated_data = self.timeframe_aggregator.get_aggregated_timeframes()
            new_candles = []
            
            # Check for new candles in each timeframe
            for timeframe, candles in aggregated_data.items():
                if candles:  # If we have data for this timeframe
                    latest_bar = candles[-1]  # Get the most recent bar
                    # Convert to our OHLCBar format
                    new_candles.append(latest_bar)
            
            # 2. For each new completed candle, calculate ATR levels
            for candle in new_candles:
                atr_levels = await self._calculate_atr_levels_for_timeframe(
                    candle.timeframe, candle
                )
                
                if atr_levels:
                    self.state.active_levels[candle.timeframe] = atr_levels
                    
                    # Store ATR levels in database  
                    try:
                        levels_data = {
                            'previous_close': atr_levels.previous_close,
                            'atr_value': atr_levels.atr,
                            'lower_trigger': atr_levels.lower_trigger,
                            'upper_trigger': atr_levels.upper_trigger,
                            'lower_0382': atr_levels.lower_0382,
                            'upper_0382': atr_levels.upper_0382,
                            'lower_0500': atr_levels.lower_0500,
                            'upper_0500': atr_levels.upper_0500,
                            'lower_0618': atr_levels.lower_0618,
                            'upper_0618': atr_levels.upper_0618,
                            'lower_0786': atr_levels.lower_0786,
                            'upper_0786': atr_levels.upper_0786,
                            'lower_1000': atr_levels.lower_1000,
                            'upper_1000': atr_levels.upper_1000,
                            'lower_1236': atr_levels.lower_1236,
                            'upper_1236': atr_levels.upper_1236,
                            'lower_1618': atr_levels.lower_1618,
                            'upper_1618': atr_levels.upper_1618,
                            'lower_2000': atr_levels.lower_2000,
                            'upper_2000': atr_levels.upper_2000,
                        }
                        await store_atr_levels(
                            timeframe=candle.timeframe,
                            session_date=candle.timestamp.strftime('%Y-%m-%d'),
                            levels_data=levels_data
                        )
                    except Exception as e:
                        logger.debug(f"Failed to store ATR levels: {e}")
                    
                    # 3. Check for level hits with current price
                    level_hits = await self._check_level_hits(
                        tick.price, atr_levels, candle.timeframe
                    )
                    hits.extend(level_hits)
            
            # 4. Also check current price against existing levels
            for timeframe, levels in self.state.active_levels.items():
                level_hits = await self._check_level_hits(
                    tick.price, levels, timeframe
                )
                hits.extend(level_hits)
            
            # 5. Process hits and log them
            for hit in hits:
                self.stats["level_hits_detected"] += 1
                
                # Log the hit
                await log_event("fibonacci_level_hit", {
                    "symbol": hit.symbol,
                    "timeframe": hit.timeframe,
                    "level_name": hit.level_name,
                    "level_value": hit.level_value,
                    "current_price": hit.current_price,
                    "direction": hit.direction,
                    "fib_ratio": hit.fib_ratio,
                    "timestamp": hit.hit_time.isoformat()
                })
            
            # Update performance stats
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.stats["avg_processing_time_ms"] = (
                (self.stats["avg_processing_time_ms"] * (self.stats["total_ticks_processed"] - 1) + processing_time) 
                / self.stats["total_ticks_processed"]
            )
            self.stats["last_calculation_time"] = datetime.now().isoformat()
            
            # Store recent hits (keep last 100)
            self.state.recent_hits.extend(hits)
            if len(self.state.recent_hits) > 100:
                self.state.recent_hits = self.state.recent_hits[-100:]
            
            return hits
            
        except Exception as e:
            logger.error(f"❌ Error processing tick: {e}")
            return []
    
    async def _calculate_atr_levels_for_timeframe(self, timeframe: str, latest_candle: OHLCBar) -> Optional[ATRLevels]:
        """Calculate ATR levels for a specific timeframe"""
        try:
            # Get historical data from our aggregator
            historical_candles = self.timeframe_aggregator.get_timeframe_history(timeframe, periods=30)
            
            # If we don't have enough historical data, bootstrap it from Schwab
            if len(historical_candles) < 14:
                logger.info(f"🔄 Bootstrapping historical data for {timeframe}...")
                await self._bootstrap_historical_data(timeframe)
                # Try again after bootstrapping
                historical_candles = self.timeframe_aggregator.get_timeframe_history(timeframe, periods=30)
                
            if len(historical_candles) < 14:  # Still not enough
                logger.warning(f"⚠️  Insufficient data for {timeframe} ATR calculation ({len(historical_candles)} bars)")
                return None
            
            # Create ATR calculator
            calculator = ATRCalculator(atr_length=14)
            
            # Add historical data
            for candle in historical_candles:
                calculator.add_price_data(
                    timeframe, candle.high, candle.low, candle.close
                )
            
            # Add latest candle
            calculator.add_price_data(
                timeframe, latest_candle.high, latest_candle.low, latest_candle.close
            )
            
            # Calculate levels
            levels = calculator.calculate_atr_levels(timeframe)
            
            if levels:
                logger.info(f"📊 Calculated {timeframe} ATR levels - ATR: {levels.atr:.2f}")
                
                await log_event("atr_levels_calculated", {
                    "timeframe": timeframe,
                    "atr": levels.atr,
                    "previous_close": levels.previous_close,
                    "timestamp": datetime.now().isoformat()
                })
            
            return levels
            
        except Exception as e:
            logger.error(f"❌ Error calculating ATR levels for {timeframe}: {e}")
            return None
    
    async def _bootstrap_historical_data(self, timeframe: str) -> bool:
        """Bootstrap historical data for a timeframe using Schwab API"""
        try:
            logger.info(f"📊 Fetching historical SPX data for {timeframe} timeframe...")
            
            # Determine how much historical data we need based on timeframe
            timeframe_days = {
                "scalp": 3,      # 4H bars: need 3 days for 14+ bars  
                "day": 30,       # Daily bars: need 30 days for 14+ bars
                "multiday": 120, # Weekly bars: need ~4 months for 14+ bars
                "swing": 365,    # Monthly bars: need 1+ year for 14+ bars
                "position": 1095, # Quarterly: need 3+ years for 14+ bars
                "long_term": 4380 # Yearly: need 12+ years for 14+ bars
            }
            
            days_needed = timeframe_days.get(timeframe, 30)
            
            # Get minute data from Schwab (this will be our base data)
            minute_candles = await self.data_collector.get_minute_data("SPX", days=min(days_needed, 7))
            
            if not minute_candles:
                logger.warning(f"⚠️  No minute data received from Schwab for bootstrapping")
                return False
            
            logger.info(f"✅ Retrieved {len(minute_candles)} minute candles from Schwab")
            
            # Feed this historical minute data into our aggregator
            for candle in minute_candles:
                self.timeframe_aggregator.add_minute_bar(
                    candle.timestamp,
                    candle.open,
                    candle.high, 
                    candle.low,
                    candle.close,
                    candle.volume
                )
            
            # Verify we now have enough data
            historical_candles = self.timeframe_aggregator.get_timeframe_history(timeframe, periods=30)
            
            logger.info(f"📈 After bootstrap: {len(historical_candles)} {timeframe} bars available")
            
            return len(historical_candles) >= 14
            
        except Exception as e:
            logger.error(f"❌ Error bootstrapping historical data for {timeframe}: {e}")
            return False
    
    async def _check_level_hits(self, current_price: float, atr_levels: ATRLevels, timeframe: str) -> List[FibLevelHit]:
        """Check if current price hits any ATR levels"""
        hits = []
        
        # Define all the levels to check
        level_checks = [
            ("lower_trigger", atr_levels.lower_trigger, "bear", 0.236),
            ("upper_trigger", atr_levels.upper_trigger, "bull", 0.236),
            ("lower_0382", atr_levels.lower_0382, "bear", 0.382),
            ("upper_0382", atr_levels.upper_0382, "bull", 0.382),
            ("lower_0500", atr_levels.lower_0500, "bear", 0.500),
            ("upper_0500", atr_levels.upper_0500, "bull", 0.500),
            ("lower_0618", atr_levels.lower_0618, "bear", 0.618),
            ("upper_0618", atr_levels.upper_0618, "bull", 0.618),
            ("lower_0786", atr_levels.lower_0786, "bear", 0.786),
            ("upper_0786", atr_levels.upper_0786, "bull", 0.786),
            ("lower_1000", atr_levels.lower_1000, "bear", 1.000),
            ("upper_1000", atr_levels.upper_1000, "bull", 1.000),
            ("lower_1236", atr_levels.lower_1236, "bear", 1.236),
            ("upper_1236", atr_levels.upper_1236, "bull", 1.236),
            ("lower_1618", atr_levels.lower_1618, "bear", 1.618),
            ("upper_1618", atr_levels.upper_1618, "bull", 1.618),
            ("lower_2000", atr_levels.lower_2000, "bear", 2.000),
            ("upper_2000", atr_levels.upper_2000, "bull", 2.000),
        ]
        
        tolerance = 0.10  # 10 cent tolerance for level hits
        
        for level_name, level_value, direction, fib_ratio in level_checks:
            if abs(current_price - level_value) <= tolerance:
                hit = FibLevelHit(
                    symbol="SPX",
                    timeframe=timeframe,
                    level_name=level_name,
                    level_value=level_value,
                    current_price=current_price,
                    hit_time=datetime.now(timezone.utc),
                    direction=direction,
                    fib_ratio=fib_ratio,
                    previous_close=atr_levels.previous_close,
                    atr_value=atr_levels.atr
                )
                hits.append(hit)
                
                logger.info(f"🎯 LEVEL HIT: {timeframe} {level_name} @ ${current_price:.2f} (target: ${level_value:.2f})")
                
                # Store level hit in database
                try:
                    hit_id = await log_level_hit(
                        timeframe=timeframe,
                        level_name=level_name, 
                        level_value=level_value,
                        hit_price=current_price,
                        direction=direction,
                        fib_ratio=fib_ratio,
                        previous_close=atr_levels.previous_close,
                        atr_value=atr_levels.atr
                    )
                    
                    # If this is a Golden Gate start (.382), start tracking sequence
                    if fib_ratio == 0.382:
                        await start_golden_gate_sequence(
                            timeframe=timeframe,
                            direction=direction,
                            start_level_hit_id=hit_id,
                            start_time=hit.hit_time.isoformat(),
                            start_price=current_price
                        )
                        logger.info(f"🚪 Golden Gate sequence started: {timeframe} {direction}")
                    
                    # If this is a Golden Gate completion (.618), complete any active sequence
                    elif fib_ratio == 0.618:
                        # Note: In a full implementation, you'd find the matching active sequence
                        # For now, we'll just log it
                        logger.info(f"🏆 Golden Gate completion detected: {timeframe} {direction}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to store level hit in database: {e}")
        
        return hits
    
    async def start_real_time_processing(self) -> AsyncGenerator[FibLevelHit, None]:
        """
        Start real-time SPX processing.
        Yields level hits as they occur.
        """
        if not await self.initialize():
            raise Exception("Failed to initialize ATR system")
        
        self.state.system_status = "running"
        logger.info("📊 Starting real-time SPX ATR processing...")
        
        try:
            async for tick in self.data_collector.stream_real_time(["SPX"]):
                hits = await self.process_market_tick(tick)
                
                for hit in hits:
                    yield hit
                    
                # Log progress every 100 ticks
                if self.stats["total_ticks_processed"] % 100 == 0:
                    logger.info(f"📈 Processed {self.stats['total_ticks_processed']} ticks, "
                              f"{self.stats['level_hits_detected']} hits detected")
        
        except Exception as e:
            logger.error(f"❌ Real-time processing error: {e}")
            self.state.system_status = "error"
            raise
        finally:
            self.state.system_status = "stopped"
    
    def get_current_levels(self, timeframe: Optional[str] = None) -> Dict[str, ATRLevels]:
        """Get current ATR levels for all timeframes or specific timeframe"""
        if timeframe:
            return {timeframe: self.state.active_levels.get(timeframe)} if timeframe in self.state.active_levels else {}
        return self.state.active_levels.copy()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "system_status": self.state.system_status,
            "current_price": self.state.current_price,
            "last_update": self.state.last_update.isoformat() if self.state.last_update else None,
            "active_timeframes": list(self.state.active_levels.keys()),
            "recent_hits_count": len(self.state.recent_hits),
            "stats": self.stats,
            "data_collector_connected": self.data_collector.connected if self.data_collector else False
        }
    
    def get_recent_hits(self, limit: int = 20) -> List[FibLevelHit]:
        """Get recent level hits"""
        return self.state.recent_hits[-limit:] if self.state.recent_hits else []

# Global system instance
_global_atr_system: Optional[SPXATRSystem] = None

async def get_atr_system() -> SPXATRSystem:
    """Get or create the global ATR system instance"""
    global _global_atr_system
    
    if _global_atr_system is None:
        _global_atr_system = SPXATRSystem()
        await _global_atr_system.initialize()
    
    return _global_atr_system

# Convenience functions for easy access
async def get_current_spx_levels() -> Dict[str, ATRLevels]:
    """Get current SPX ATR levels for all timeframes"""
    system = await get_atr_system()
    return system.get_current_levels()

async def start_spx_level_tracking() -> AsyncGenerator[FibLevelHit, None]:
    """Start tracking SPX levels and yield hits as they occur"""
    system = await get_atr_system()
    async for hit in system.start_real_time_processing():
        yield hit

async def get_spx_system_status() -> Dict[str, Any]:
    """Get SPX ATR system status"""
    system = await get_atr_system()
    return system.get_system_status()

if __name__ == "__main__":
    # Test the ATR system
    async def test_atr_system():
        logger.info("🧪 Testing SPX ATR System...")
        
        try:
            # Test system initialization
            system = await get_atr_system()
            status = system.get_system_status()
            logger.info(f"✅ System Status: {status['system_status']}")
            
            # Test current levels
            levels = system.get_current_levels()
            logger.info(f"📊 Active timeframes: {list(levels.keys())}")
            
            # Test a few real-time ticks
            logger.info("📈 Processing real-time data for 30 seconds...")
            hit_count = 0
            
            async for hit in system.start_real_time_processing():
                hit_count += 1
                logger.info(f"🎯 Hit #{hit_count}: {hit.timeframe} {hit.level_name} @ ${hit.current_price:.2f}")
                
                # Stop after 30 seconds or 5 hits
                if hit_count >= 5:
                    break
            
            logger.info(f"✅ Test completed - {hit_count} level hits detected")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
    
    asyncio.run(test_atr_system())
