import asyncio
import json
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator, Optional
import aiohttp
import aiosqlite
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

from database import get_db, log_event

class DataFeed(ABC):
    """Abstract base class for market data feeds."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the data source. Returns True if successful."""
        pass
    
    @abstractmethod
    async def stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream market data ticks."""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the data source."""
        pass

class SchwabFeed(DataFeed):
    """Schwab/ThinkOrSwim market data feed."""
    
    def __init__(self, symbol: str = "SPY"):
        super().__init__(symbol)
        self.session = None
        self.ws = None
        self.connected = False
        self.token_file = os.path.expanduser("~/.schwab_tokens.json")
        
    async def connect(self) -> bool:
        """Connect to Schwab WebSocket feed."""
        try:
            # For now, we'll use a simulated Schwab-like feed
            # TODO: Implement actual Schwab OAuth and WebSocket connection
            self.session = aiohttp.ClientSession()
            self.connected = True
            await self._log_event("schwab_connected", {"symbol": self.symbol})
            return True
        except Exception as e:
            await self._log_event("schwab_connection_error", {"error": str(e)})
            return False
    
    async def stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream real-time market data."""
        if not self.connected:
            raise RuntimeError("Not connected to Schwab feed")
        
        # For Week 1, we'll simulate Schwab data with more realistic patterns
        # TODO: Replace with actual Schwab WebSocket stream
        base_price = 450.0  # SPY-like base
        price = base_price
        
        while self.connected:
            try:
                # Simulate realistic price movements
                change = (time.time() % 100 - 50) * 0.1  # Oscillating pattern
                price += change
                
                # Add some volatility
                if time.time() % 30 < 5:  # Every 30 seconds, 5 seconds of volatility
                    price += (time.time() % 10 - 5) * 0.5
                
                tick_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "symbol": self.symbol,
                    "price": round(price, 2),
                    "volume": int(1000 + (time.time() % 1000) * 50),
                    "bid": round(price - 0.01, 2),
                    "ask": round(price + 0.01, 2),
                    "change": round(change, 2),
                    "change_percent": round((change / base_price) * 100, 3),
                    "tick_id": int(time.time() * 1000),
                    "source": "schwab_sim"
                }
                
                await self._log_event("tick", tick_data)
                yield tick_data
                
                await asyncio.sleep(1)  # 1-Hz stream
                
            except Exception as e:
                await self._log_event("schwab_stream_error", {"error": str(e)})
                await asyncio.sleep(5)  # Wait before retrying
    
    async def disconnect(self):
        """Disconnect from Schwab feed."""
        self.connected = False
        if self.session:
            await self.session.close()
        await self._log_event("schwab_disconnected", {})
    
    async def _log_event(self, event_type: str, payload: Dict[str, Any]):
        """Log events to database."""
        try:
            await log_event(event_type, payload)
        except Exception as e:
            print(f"Failed to log event {event_type}: {e}")

class SimulatedFeed(DataFeed):
    """Fallback simulated feed for testing."""
    
    def __init__(self, symbol: str = "SPY"):
        super().__init__(symbol)
        self.connected = False
        self.tick = 0
    
    async def connect(self) -> bool:
        """Connect to simulated feed."""
        self.connected = True
        return True
    
    async def stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream simulated market data."""
        while self.connected:
            tick_data = {
                "tick": self.tick,
                "value": 100 + self.tick,
                "timestamp": datetime.utcnow().isoformat(),
                "symbol": self.symbol,
                "source": "simulated"
            }
            
            self.tick += 1
            yield tick_data
            await asyncio.sleep(1)
    
    async def disconnect(self):
        """Disconnect from simulated feed."""
        self.connected = False

class YFinanceFeed(DataFeed):
    """Real-time SPY data feed using yfinance."""
    
    def __init__(self, symbol: str = "SPY"):
        super().__init__(symbol)
        self.last_update = None
        self.base_price = None
        self.update_interval = 60  # 1 minute updates
        self.connected = False
    
    async def _log_event(self, event_type: str, payload: Dict[str, Any]):
        """Log events to database."""
        try:
            await log_event(event_type, payload)
        except Exception as e:
            print(f"Failed to log event {event_type}: {e}")
    
    async def connect(self) -> bool:
        """Connect to yfinance feed."""
        try:
            # Test connection by getting current price
            ticker = yf.Ticker(self.symbol)
            info = ticker.info
            if info.get('regularMarketPrice'):
                self.base_price = info['regularMarketPrice']
                self.connected = True
                await self._log_event("yfinance_connected", {
                    "symbol": self.symbol,
                    "base_price": self.base_price,
                    "timestamp": datetime.utcnow().isoformat()
                })
                return True
            else:
                await self._log_event("yfinance_connection_failed", {
                    "symbol": self.symbol,
                    "error": "No price data available"
                })
                return False
        except Exception as e:
            await self._log_event("yfinance_connection_error", {
                "symbol": self.symbol,
                "error": str(e)
            })
            return False
    
    async def get_latest_data(self) -> Optional[Dict[str, Any]]:
        """Get the latest 1-minute data for the symbol."""
        try:
            # Get 1-minute data for today
            ticker = yf.Ticker(self.symbol)
            data = ticker.history(period="1d", interval="1m")
            
            if data.empty:
                return None
            
            # Get the latest candle
            latest = data.iloc[-1]
            
            # Calculate change from previous close
            if len(data) > 1:
                prev_close = data.iloc[-2]['Close']
                change = latest['Close'] - prev_close
                change_percent = (change / prev_close) * 100
            else:
                change = 0
                change_percent = 0
            
            tick_data = {
                "timestamp": latest.name.isoformat(),
                "symbol": self.symbol,
                "price": round(latest['Close'], 2),
                "volume": int(latest['Volume']),
                "bid": round(latest['Close'] - 0.01, 2),  # Approximate bid
                "ask": round(latest['Close'] + 0.01, 2),  # Approximate ask
                "change": round(change, 2),
                "change_percent": round(change_percent, 3),
                "open": round(latest['Open'], 2),
                "high": round(latest['High'], 2),
                "low": round(latest['Low'], 2),
                "tick_id": int(time.time() * 1000),
                "source": "yfinance"
            }
            
            return tick_data
            
        except Exception as e:
            await self._log_event("yfinance_data_error", {
                "symbol": self.symbol,
                "error": str(e)
            })
            return None
    
    async def stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream real-time market data from yfinance."""
        if not self.connected:
            raise RuntimeError("Not connected to yfinance feed")
        
        while self.connected:
            try:
                tick_data = await self.get_latest_data()
                
                if tick_data:
                    await self._log_event("yfinance_tick", tick_data)
                    yield tick_data
                else:
                    # Fallback to simulated data if yfinance fails
                    await self._log_event("yfinance_fallback", {
                        "symbol": self.symbol,
                        "message": "Using simulated data as fallback"
                    })
                    
                    # Generate realistic fallback data
                    base_price = self.base_price or 450.0
                    change = (time.time() % 100 - 50) * 0.1
                    price = base_price + change
                    
                    fallback_data = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "symbol": self.symbol,
                        "price": round(price, 2),
                        "volume": int(1000 + (time.time() % 1000) * 50),
                        "bid": round(price - 0.01, 2),
                        "ask": round(price + 0.01, 2),
                        "change": round(change, 2),
                        "change_percent": round((change / base_price) * 100, 3),
                        "open": round(price - 0.05, 2),
                        "high": round(price + 0.05, 2),
                        "low": round(price - 0.05, 2),
                        "tick_id": int(time.time() * 1000),
                        "source": "yfinance_fallback"
                    }
                    
                    yield fallback_data
                
                # Wait for next update (1 minute)
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                await self._log_event("yfinance_stream_error", {"error": str(e)})
                await asyncio.sleep(5)  # Wait before retrying
    
    async def get_historical_data(self, start_date: str, end_date: str, interval: str = "1d") -> pd.DataFrame:
        """Get historical data for backtesting."""
        try:
            ticker = yf.Ticker(self.symbol)
            data = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if data.empty:
                return pd.DataFrame()
            
            # Format data for backtesting
            formatted_data = []
            for date, row in data.iterrows():
                formatted_data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'open': round(row['Open'], 2),
                    'high': round(row['High'], 2),
                    'low': round(row['Low'], 2),
                    'close': round(row['Close'], 2),
                    'volume': int(row['Volume'])
                })
            
            return pd.DataFrame(formatted_data)
            
        except Exception as e:
            await self._log_event("yfinance_historical_error", {
                "symbol": self.symbol,
                "start_date": start_date,
                "end_date": end_date,
                "error": str(e)
            })
            return pd.DataFrame()
    
    async def disconnect(self):
        """Disconnect from yfinance feed."""
        self.connected = False
        # No persistent connection to close, but method required for ABC
        await self._log_event("yfinance_disconnected", {"symbol": self.symbol})

# Factory function to get the appropriate data feed
def get_data_feed(symbol: str = "SPY", use_real_data: bool = False) -> DataFeed:
    """Get the appropriate data feed based on configuration."""
    if use_real_data:
        return YFinanceFeed(symbol)
    else:
        return SimulatedFeed(symbol) 