"""
Real-time Indicator Calculation Service
Calculates and stores indicator values across all timeframes
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
from data_providers import get_provider
from database import log_event, get_db
from indicators.technical.atr import ATRIndicator


class IndicatorService:
    """Service for calculating and storing real-time indicators."""
    
    def __init__(self):
        self.provider = get_provider()
        self.timeframes = [
            "1m", "3m", "5m", "10m", "15m", "30m",  # Intraday
            "1h", "4h",  # Hourly
            "1d", "1w"   # Daily/Weekly
        ]
        self.trading_timeframes = [
            "scalp", "day", "multiday", "swing", "position", "long_term"
        ]
        self.symbols = ["SPY", "QQQ", "IWM", "DIA"]  # Default symbols
        self.indicator_cache = {}
        self.cache_ttl = 300  # 5 minutes cache
    
    async def calculate_all_indicators(self, symbol: str = "SPY"):
        """Calculate all indicators for a symbol across all timeframes."""
        try:
            results = {}
            
            for timeframe in self.timeframes + self.trading_timeframes:
                timeframe_results = await self.calculate_timeframe_indicators(symbol, timeframe)
                results[timeframe] = timeframe_results
                
                # Store in database
                await self.store_indicator_data(symbol, timeframe, timeframe_results)
            
            # Cache results
            self.indicator_cache[f"{symbol}_all"] = {
                "data": results,
                "timestamp": datetime.now()
            }
            
            await log_event("indicators_calculated", {
                "symbol": symbol,
                "timeframes": len(results),
                "status": "success"
            })
            
            return results
            
        except Exception as e:
            await log_event("indicator_calculation_error", {
                "symbol": symbol,
                "error": str(e)
            })
            return {}
    
    async def calculate_timeframe_indicators(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Calculate indicators for a specific timeframe."""
        try:
            results = {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "timeframe": timeframe,
                "indicators": {}
            }
            
            # Get current price
            current_price = await self.provider.get_latest_price(symbol)
            results["current_price"] = current_price
            
            # Calculate ATR
            atr_14 = await self.provider.get_atr(symbol, timeframe, 14)
            atr_21 = await self.provider.get_atr(symbol, timeframe, 21)
            results["indicators"]["atr"] = {
                "atr_14": atr_14,
                "atr_21": atr_21,
                "atr_levels": ATRIndicator.calculate(current_price, atr_14)
            }
            
            # Calculate EMAs
            ema_9 = await self.provider.get_ema(symbol, timeframe, 9)
            ema_21 = await self.provider.get_ema(symbol, timeframe, 21)
            ema_50 = await self.provider.get_ema(symbol, timeframe, 50)
            ema_200 = await self.provider.get_ema(symbol, timeframe, 200)
            
            results["indicators"]["ema"] = {
                "ema_9": ema_9,
                "ema_21": ema_21,
                "ema_50": ema_50,
                "ema_200": ema_200,
                "trend": self.analyze_ema_trend(ema_9, ema_21, ema_50, ema_200)
            }
            
            # Calculate SMAs
            sma_20 = await self.provider.get_sma(symbol, timeframe, 20)
            sma_50 = await self.provider.get_sma(symbol, timeframe, 50)
            sma_200 = await self.provider.get_sma(symbol, timeframe, 200)
            
            results["indicators"]["sma"] = {
                "sma_20": sma_20,
                "sma_50": sma_50,
                "sma_200": sma_200
            }
            
            # Calculate pivot ribbon (simplified)
            pivot_data = await self.calculate_pivot_ribbon(symbol, timeframe)
            results["indicators"]["pivot_ribbon"] = pivot_data
            
            # Calculate support/resistance levels
            support_resistance = await self.calculate_support_resistance(symbol, timeframe)
            results["indicators"]["support_resistance"] = support_resistance
            
            return results
            
        except Exception as e:
            await log_event("timeframe_indicator_error", {
                "symbol": symbol,
                "timeframe": timeframe,
                "error": str(e)
            })
            return {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "timeframe": timeframe,
                "error": str(e)
            }
    
    def analyze_ema_trend(self, ema_9: float, ema_21: float, ema_50: float, ema_200: float) -> str:
        """Analyze EMA trend alignment."""
        if ema_9 > ema_21 > ema_50 > ema_200:
            return "strong_bullish"
        elif ema_9 < ema_21 < ema_50 < ema_200:
            return "strong_bearish"
        elif ema_9 > ema_21 and ema_50 > ema_200:
            return "bullish"
        elif ema_9 < ema_21 and ema_50 < ema_200:
            return "bearish"
        else:
            return "neutral"
    
    async def calculate_pivot_ribbon(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Calculate pivot ribbon indicators."""
        try:
            # Get recent data for pivot calculations
            data = await self.provider.get_ohlcv_data(symbol, timeframe, 50)
            
            if len(data) < 3:
                return {"error": "insufficient_data"}
            
            # Calculate pivot points
            latest = data.iloc[-1]
            prev = data.iloc[-2]
            
            pivot = (latest['high'] + latest['low'] + latest['close']) / 3
            r1 = (2 * pivot) - latest['low']
            s1 = (2 * pivot) - latest['high']
            r2 = pivot + (latest['high'] - latest['low'])
            s2 = pivot - (latest['high'] - latest['low'])
            
            # Determine position relative to pivot
            current_price = latest['close']
            position = "above_pivot" if current_price > pivot else "below_pivot"
            
            return {
                "pivot": round(pivot, 4),
                "r1": round(r1, 4),
                "r2": round(r2, 4),
                "s1": round(s1, 4),
                "s2": round(s2, 4),
                "position": position,
                "strength": "strong" if abs(current_price - pivot) > (latest['high'] - latest['low']) * 0.1 else "weak"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def calculate_support_resistance(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Calculate support and resistance levels."""
        try:
            data = await self.provider.get_ohlcv_data(symbol, timeframe, 100)
            
            if len(data) < 20:
                return {"error": "insufficient_data"}
            
            # Simple support/resistance calculation
            highs = data['high'].nlargest(5).tolist()
            lows = data['low'].nsmallest(5).tolist()
            
            current_price = data['close'].iloc[-1]
            
            # Find nearest levels
            resistance_levels = [h for h in highs if h > current_price]
            support_levels = [l for l in lows if l < current_price]
            
            return {
                "resistance_levels": sorted(resistance_levels)[:3],
                "support_levels": sorted(support_levels, reverse=True)[:3],
                "nearest_resistance": min(resistance_levels) if resistance_levels else None,
                "nearest_support": max(support_levels) if support_levels else None
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def store_indicator_data(self, symbol: str, timeframe: str, data: Dict[str, Any]):
        """Store indicator data in the database."""
        try:
            db = get_db()
            cursor = db.cursor()
            
            # Create indicators table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS indicator_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timeframe, timestamp)
                )
            """)
            
            # Insert or update indicator data
            cursor.execute("""
                INSERT OR REPLACE INTO indicator_data (symbol, timeframe, data, timestamp)
                VALUES (?, ?, ?, ?)
            """, (symbol, timeframe, json.dumps(data), datetime.now().isoformat()))
            
            db.commit()
            
        except Exception as e:
            await log_event("indicator_storage_error", {
                "symbol": symbol,
                "timeframe": timeframe,
                "error": str(e)
            })
    
    async def get_latest_indicators(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Get the latest indicator data for a symbol and timeframe."""
        try:
            # Check cache first
            cache_key = f"{symbol}_{timeframe}"
            if cache_key in self.indicator_cache:
                cache_entry = self.indicator_cache[cache_key]
                if (datetime.now() - cache_entry["timestamp"]).seconds < self.cache_ttl:
                    return cache_entry["data"]
            
            # Get from database
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute("""
                SELECT data FROM indicator_data 
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (symbol, timeframe))
            
            result = cursor.fetchone()
            if result:
                data = json.loads(result[0])
                # Update cache
                self.indicator_cache[cache_key] = {
                    "data": data,
                    "timestamp": datetime.now()
                }
                return data
            
            # If not in database, calculate fresh
            return await self.calculate_timeframe_indicators(symbol, timeframe)
            
        except Exception as e:
            await log_event("get_indicators_error", {
                "symbol": symbol,
                "timeframe": timeframe,
                "error": str(e)
            })
            return None
    
    async def start_periodic_calculation(self, interval_seconds: int = 300):
        """Start periodic calculation of indicators."""
        while True:
            try:
                for symbol in self.symbols:
                    await self.calculate_all_indicators(symbol)
                
                await log_event("periodic_indicator_update", {
                    "symbols": self.symbols,
                    "timeframes": len(self.timeframes + self.trading_timeframes)
                })
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                await log_event("periodic_calculation_error", {"error": str(e)})
                await asyncio.sleep(60)  # Wait 1 minute before retrying


# Global service instance
_indicator_service = None

def get_indicator_service() -> IndicatorService:
    """Get the global indicator service instance."""
    global _indicator_service
    if _indicator_service is None:
        _indicator_service = IndicatorService()
    return _indicator_service
