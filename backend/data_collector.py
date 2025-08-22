#!/usr/bin/env python3
"""
Schwab-Only Data Collector Module
Clean, focused data collection exclusively from Schwab API for maximum reliability.
Consolidates all duplicate data feed files into one modular component.
"""

import asyncio
import json
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
import logging

from database import log_event
from schwab_config import SchwabOAuthManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarketTick:
    """Standardized market tick data structure"""
    symbol: str
    price: float
    high: float
    low: float
    volume: int
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None

@dataclass
class OHLCCandle:
    """OHLC candle data structure for timeframe aggregation"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    timeframe: str

class SchwabDataCollector:
    """
    Pure Schwab API data collector - Single source of truth for market data.
    Replaces 8+ duplicate data feed files with one clean, modular implementation.
    """
    
    def __init__(self, oauth_manager: SchwabOAuthManager):
        self.oauth_manager = oauth_manager
        self.base_url = "https://api.schwabapi.com"
        self.connected = False
        
        # Symbol mapping for Schwab API - Direct SPX access
        self.symbol_map = {
            "SPX": "$SPX",      # S&P 500 Index - direct access!
        }
        
        # Track active symbols and performance
        self.active_symbols = set()
        self.stats = {
            "api_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_request_time": None,
            "connection_status": "disconnected"
        }
        
        logger.info("🎯 Schwab Data Collector initialized")
    
    def _map_symbol(self, symbol: str) -> str:
        """Map internal symbol to Schwab API format"""
        return self.symbol_map.get(symbol, symbol)
    
    async def _make_api_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make authenticated API request to Schwab with error handling"""
        self.stats["api_requests"] += 1
        self.stats["last_request_time"] = datetime.now().isoformat()
        
        try:
            # Load tokens if not already loaded
            await self.oauth_manager.load_tokens()
            access_token = await self.oauth_manager.get_valid_access_token()
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                # Don't send Content-Type for GET requests
            }
            
            # Manually construct URL to avoid aiohttp encoding issues with $SPX
            if params and 'symbols' in params and '$SPX' in params['symbols']:
                # Special handling for $SPX - construct URL manually
                url = f"{self.base_url}{endpoint}?symbols=%24SPX"
                params = None
            else:
                url = f"{self.base_url}{endpoint}"
            
            logger.info(f"🔗 Final URL: {url}")
            
            # Create SSL context that ignores certificate verification (for macOS)
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        self.stats["successful_requests"] += 1
                        return await response.json()
                    else:
                        self.stats["failed_requests"] += 1
                        error_text = await response.text()
                        logger.error(f"Schwab API request failed: {response.status}")
                        logger.error(f"URL: {url}")
                        logger.error(f"Params: {params}")
                        logger.error(f"Response: {error_text}")
                        raise Exception(f"Schwab API error: {response.status} - {error_text}")
                        
        except Exception as e:
            self.stats["failed_requests"] += 1
            logger.error(f"Schwab API request error: {e}")
            raise
    
    async def connect(self) -> bool:
        """Connect to Schwab API and validate authentication"""
        try:
            logger.info("🔗 Connecting to Schwab API...")
            
            # Test connection with SPX quote  
            test_response = await self._make_api_request(
                "/marketdata/v1/quotes", 
                {"symbols": "$SPX"}
            )
            
            logger.info(f"🔍 Response keys: {list(test_response.keys())}")
            logger.info(f"🔍 Full response: {test_response}")
            
            if "$SPX" in test_response:
                spx_data = test_response["$SPX"]
                logger.info(f"🔍 SPX data keys: {list(spx_data.keys())}")
                
                # Check for price in quote section
                if "quote" in spx_data and "lastPrice" in spx_data["quote"]:
                    price = spx_data["quote"]["lastPrice"]
                elif "lastPrice" in spx_data:
                    price = spx_data["lastPrice"]
                else:
                    logger.error(f"❌ No price found in SPX data: {spx_data}")
                    return False
                    
                self.connected = True
                self.stats["connection_status"] = "connected"
                
                logger.info(f"✅ Schwab API connected successfully - SPX: ${price:.2f}")
                
                await log_event("schwab_api_connected", {
                    "timestamp": datetime.now().isoformat(),
                    "test_price": price
                })
                return True
            else:
                logger.error(f"❌ No $SPX in response: {test_response}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Schwab API: {e}")
            self.stats["connection_status"] = "failed"
            await log_event("schwab_api_connection_failed", {"error": str(e)})
            return False
    
    async def get_current_price(self, symbol: str) -> Optional[MarketTick]:
        """Get current market price for symbol"""
        if not self.connected:
            if not await self.connect():
                return None
        
        try:
            schwab_symbol = self._map_symbol(symbol)
            logger.info(f"🔍 Getting quote for {symbol} -> {schwab_symbol}")
            
            # Try the quote endpoint with symbol as parameter
            # Don't URL encode here - aiohttp will handle it properly
            response = await self._make_api_request(
                "/marketdata/v1/quotes", 
                {"symbols": schwab_symbol}
            )
            
            if schwab_symbol in response:
                data = response[schwab_symbol]
                
                # Extract price data from quote section for indices
                if "quote" in data:
                    quote = data["quote"]
                    last_price = quote.get("lastPrice", 0.0)
                    high_price = quote.get("highPrice", last_price) or quote.get("52WeekHigh", last_price)
                    low_price = quote.get("lowPrice", last_price) or quote.get("52WeekLow", last_price)
                    volume = quote.get("totalVolume", 0)
                else:
                    # Fallback for other data structures
                    last_price = data.get("lastPrice", 0.0)
                    high_price = data.get("highPrice", last_price)
                    low_price = data.get("lowPrice", last_price)
                    volume = data.get("totalVolume", 0)
                
                if last_price > 0:
                    return MarketTick(
                        symbol=symbol,
                        price=last_price,
                        high=high_price,
                        low=low_price,
                        volume=volume,
                        timestamp=datetime.now(timezone.utc),
                        bid=quote.get("bidPrice"),
                        ask=quote.get("askPrice")
                    )
            
            logger.warning(f"No price data found for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    async def get_minute_data(self, symbol: str, days: int = 1) -> List[OHLCCandle]:
        """
        Get minute-level OHLC data - Foundation for your ATR level tracking.
        This is the ONLY timeframe you need to collect - everything else is aggregation.
        """
        if not self.connected:
            if not await self.connect():
                return []
        
        try:
            schwab_symbol = self._map_symbol(symbol)
            
            # Get minute data from Schwab
            response = await self._make_api_request(
                "/marketdata/v1/pricehistory",
                {
                    "symbol": schwab_symbol,
                    "periodType": "day",
                    "period": days,
                    "frequencyType": "minute",
                    "frequency": 1,
                    "needExtendedHoursData": False  # Regular trading hours only
                }
            )
            
            candles = []
            if "candles" in response:
                for candle_data in response["candles"]:
                    # Convert timestamp from milliseconds to datetime
                    timestamp = datetime.fromtimestamp(
                        candle_data["datetime"] / 1000, 
                        timezone.utc
                    )
                    
                    candle = OHLCCandle(
                        symbol=symbol,
                        timestamp=timestamp,
                        open=candle_data["open"],
                        high=candle_data["high"],
                        low=candle_data["low"],
                        close=candle_data["close"],
                        volume=candle_data["volume"],
                        timeframe="1m"
                    )
                    candles.append(candle)
            
            logger.info(f"✅ Retrieved {len(candles)} minute candles for {symbol}")
            
            # Log data collection for tracking
            await log_event("minute_data_collected", {
                "symbol": symbol,
                "candle_count": len(candles),
                "days": days,
                "timestamp": datetime.now().isoformat()
            })
            
            return candles
            
        except Exception as e:
            logger.error(f"Error getting minute data for {symbol}: {e}")
            return []
    
    async def get_daily_data(self, symbol: str, days: int = 30) -> List[OHLCCandle]:
        """Get daily OHLC data for ATR calculations"""
        if not self.connected:
            if not await self.connect():
                return []
        
        try:
            schwab_symbol = self._map_symbol(symbol)
            
            response = await self._make_api_request(
                "/marketdata/v1/pricehistory",
                {
                    "symbol": schwab_symbol,
                    "periodType": "day",
                    "period": days,
                    "frequencyType": "daily",
                    "frequency": 1,
                    "needExtendedHoursData": False
                }
            )
            
            candles = []
            if "candles" in response:
                for candle_data in response["candles"]:
                    timestamp = datetime.fromtimestamp(
                        candle_data["datetime"] / 1000, 
                        timezone.utc
                    )
                    
                    candle = OHLCCandle(
                        symbol=symbol,
                        timestamp=timestamp,
                        open=candle_data["open"],
                        high=candle_data["high"],
                        low=candle_data["low"],
                        close=candle_data["close"],
                        volume=candle_data["volume"],
                        timeframe="1d"
                    )
                    candles.append(candle)
            
            logger.info(f"✅ Retrieved {len(candles)} daily candles for {symbol}")
            return candles
            
        except Exception as e:
            logger.error(f"Error getting daily data for {symbol}: {e}")
            return []
    
    async def stream_real_time(self, symbols: List[str], interval_seconds: float = 2.0) -> AsyncGenerator[MarketTick, None]:
        """
        Stream real-time price data for your ATR level tracking.
        Optimized for Schwab API rate limits (120 requests/minute).
        """
        if not self.connected:
            if not await self.connect():
                return
        
        self.active_symbols.update(symbols)
        logger.info(f"📊 Starting real-time stream for {symbols} (interval: {interval_seconds}s)")
        
        # Calculate safe interval based on Schwab rate limits
        # 120 requests/minute = 2 requests/second max
        safe_interval = max(interval_seconds, len(symbols) * 0.6)  # 0.6s per symbol minimum
        
        while True:
            try:
                for symbol in symbols:
                    tick = await self.get_current_price(symbol)
                    if tick:
                        yield tick
                        
                        # Log significant price movements for debugging
                        if symbol == "SPX":
                            await log_event("spx_tick", {
                                "price": tick.price,
                                "timestamp": tick.timestamp.isoformat()
                            })
                
                # Respect API rate limits
                await asyncio.sleep(safe_interval)
                
            except Exception as e:
                logger.error(f"Error in real-time stream: {e}")
                # Back off on errors
                await asyncio.sleep(min(safe_interval * 2, 30.0))
    
    async def get_multi_symbol_quotes(self, symbols: List[str]) -> Dict[str, MarketTick]:
        """Get current quotes for multiple symbols in a single API call"""
        if not self.connected:
            if not await self.connect():
                return {}
        
        try:
            # Map symbols and create batch request
            schwab_symbols = [self._map_symbol(symbol) for symbol in symbols]
            symbol_list = ",".join(schwab_symbols)
            
            response = await self._make_api_request(
                "/marketdata/v1/quotes",
                {"symbols": symbol_list}
            )
            
            results = {}
            for symbol, schwab_symbol in zip(symbols, schwab_symbols):
                if schwab_symbol in response:
                    quote = response[schwab_symbol]
                    
                    if quote.get("lastPrice", 0) > 0:
                        results[symbol] = MarketTick(
                            symbol=symbol,
                            price=quote.get("lastPrice", 0.0),
                            high=quote.get("highPrice", 0.0),
                            low=quote.get("lowPrice", 0.0),
                            volume=quote.get("totalVolume", 0),
                            timestamp=datetime.now(timezone.utc),
                            bid=quote.get("bidPrice"),
                            ask=quote.get("askPrice")
                        )
            
            logger.info(f"✅ Retrieved quotes for {len(results)}/{len(symbols)} symbols")
            return results
            
        except Exception as e:
            logger.error(f"Error getting multi-symbol quotes: {e}")
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collector performance statistics"""
        success_rate = 0
        if self.stats["api_requests"] > 0:
            success_rate = (self.stats["successful_requests"] / self.stats["api_requests"]) * 100
        
        return {
            **self.stats,
            "success_rate_percent": round(success_rate, 2),
            "active_symbols": list(self.active_symbols),
            "symbol_mappings": self.symbol_map
        }
    
    async def disconnect(self):
        """Clean shutdown"""
        self.connected = False
        self.stats["connection_status"] = "disconnected"
        logger.info("📡 Schwab Data Collector disconnected")

# Global collector instance for module-level access
_global_collector: Optional[SchwabDataCollector] = None

async def get_data_collector(oauth_manager: Optional[SchwabOAuthManager] = None) -> SchwabDataCollector:
    """Get or create the global Schwab data collector instance"""
    global _global_collector
    
    if _global_collector is None:
        if oauth_manager is None:
            # Try to create oauth manager with default config
            from schwab_config import get_schwab_config, SchwabOAuthManager
            config = get_schwab_config()
            
            if config is None:
                logger.error("❌ No Schwab configuration found!")
                logger.error("   Set environment variables:")
                logger.error("   - SCHWAB_CLIENT_ID")
                logger.error("   - SCHWAB_CLIENT_SECRET") 
                logger.error("   - SCHWAB_REDIRECT_URI (optional)")
                raise Exception("Schwab configuration not found")
            
            oauth_manager = SchwabOAuthManager(
                client_id=config.client_id,
                client_secret=config.client_secret,
                redirect_uri=config.redirect_uri
            )
        
        _global_collector = SchwabDataCollector(oauth_manager)
        await _global_collector.connect()
    
    return _global_collector

# Convenience functions for your ATR level tracking
async def get_spx_current_price() -> Optional[MarketTick]:
    """Get current SPX price - your primary symbol"""
    collector = await get_data_collector()
    return await collector.get_current_price("SPX")

async def get_spx_minute_data(days: int = 1) -> List[OHLCCandle]:
    """Get SPX minute data - foundation for all timeframe aggregation"""
    collector = await get_data_collector()
    return await collector.get_minute_data("SPX", days)

async def get_spx_daily_data(days: int = 30) -> List[OHLCCandle]:
    """Get SPX daily data for ATR calculations"""
    collector = await get_data_collector()
    return await collector.get_daily_data("SPX", days)

async def stream_spx_real_time() -> AsyncGenerator[MarketTick, None]:
    """Stream SPX real-time data for level tracking"""
    collector = await get_data_collector()
    async for tick in collector.stream_real_time(["SPX"]):
        yield tick

async def get_spx_snapshot() -> Dict[str, MarketTick]:
    """Get current SPX snapshot"""
    collector = await get_data_collector()
    spx_tick = await collector.get_current_price("SPX")
    return {"SPX": spx_tick} if spx_tick else {}

if __name__ == "__main__":
    # Test the Schwab data collector
    async def test_schwab_collector():
        logger.info("🧪 Testing Schwab Data Collector...")
        
        try:
            # Test current price
            spx_tick = await get_spx_current_price()
            if spx_tick:
                logger.info(f"✅ SPX Current: ${spx_tick.price:.2f} (High: ${spx_tick.high:.2f}, Low: ${spx_tick.low:.2f})")
            
            # Test minute data
            minute_candles = await get_spx_minute_data(1)
            logger.info(f"✅ Retrieved {len(minute_candles)} minute candles")
            
            # Test daily data  
            daily_candles = await get_spx_daily_data(5)
            logger.info(f"✅ Retrieved {len(daily_candles)} daily candles")
            
            # Test SPX snapshot
            snapshot = await get_spx_snapshot()
            logger.info(f"✅ SPX snapshot: {list(snapshot.keys())}")
            
            # Get performance stats
            collector = await get_data_collector()
            stats = collector.get_stats()
            logger.info(f"📊 Performance: {stats['success_rate_percent']:.1f}% success rate")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
    
    asyncio.run(test_schwab_collector())