import asyncio
import json
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator, Optional
import aiohttp
import aiosqlite
from datetime import datetime, timedelta
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

# Factory function to get the appropriate data feed
def get_data_feed(symbol: str = "SPY", use_real_data: bool = False) -> DataFeed:
    """Get the appropriate data feed based on configuration."""
    if use_real_data:
        return SchwabFeed(symbol)
    else:
        return SimulatedFeed(symbol) 