"""
Data Provider Abstraction Layer
Allows easy switching between different data sources (Schwab, pure stock data)
"""

import os
import asyncio
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import aiohttp
from database import log_event
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import websockets
import pandas as pd
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class DataProviderType(Enum):
    SCHWAB = "schwab"
    PURE_STOCK_DATA = "pure_stock_data"

@dataclass
class MarketData:
    symbol: str
    price: float
    bid: float
    ask: float
    volume: int
    timestamp: datetime
    change: float
    change_percent: float
    high: float
    low: float
    open: float
    previous_close: float
    provider: str

class BaseDataProvider:
    def __init__(self):
        self.name = "base"
    
    async def get_quote(self, symbol: str) -> Optional[MarketData]:
        raise NotImplementedError
    
    async def get_historical_data(self, symbol: str, period: str = "1d", interval: str = "1m") -> Optional[pd.DataFrame]:
        raise NotImplementedError
    
    async def get_option_chain(self, symbol: str) -> Optional[Dict]:
        raise NotImplementedError
    
    async def get_market_hours(self) -> Optional[Dict]:
        raise NotImplementedError

class SchwabStreamerProvider(BaseDataProvider):
    def __init__(self, access_token: str, schwab_client_customer_id: str, 
                 schwab_client_channel: str = "N9", schwab_client_function_id: str = "APIAPP"):
        self.name = "schwab_streamer"
        self.access_token = access_token
        self.schwab_client_customer_id = schwab_client_customer_id
        self.schwab_client_channel = schwab_client_channel
        self.schwab_client_function_id = schwab_client_function_id
        self.websocket = None
        self.connected = False
        self.request_id = 0
        self.schwab_client_correl_id = str(uuid.uuid4())
        self.subscriptions = {}
        self.data_callbacks = {}
        self.heartbeat_callbacks = []
        
        # Streamer endpoints (these would come from GET User Preference endpoint)
        self.streamer_url = "wss://streamer.schwab.com/streamer"
        
        # Field mappings for LEVELONE_EQUITIES
        self.equity_fields = {
            'symbol': '0',
            'bid_price': '1',
            'ask_price': '2', 
            'last_price': '3',
            'bid_size': '4',
            'ask_size': '5',
            'ask_id': '6',
            'bid_id': '7',
            'total_volume': '8',
            'last_size': '9',
            'high_price': '10',
            'low_price': '11',
            'close_price': '12',
            'exchange_id': '13',
            'marginable': '14',
            'description': '15',
            'last_id': '16',
            'open_price': '17',
            'net_change': '18',
            '52_week_high': '19',
            '52_week_low': '20',
            'pe_ratio': '21',
            'dividend_amount': '22',
            'dividend_yield': '23',
            'nav': '24',
            'exchange_name': '25',
            'dividend_date': '26',
            'regular_market_quote': '27',
            'regular_market_trade': '28',
            'regular_market_last_price': '29',
            'regular_market_last_size': '30',
            'regular_market_net_change': '31',
            'security_status': '32',
            'mark_price': '33',
            'quote_time': '34',
            'trade_time': '35',
            'regular_market_trade_time': '36',
            'bid_time': '37',
            'ask_time': '38',
            'ask_mic_id': '39',
            'bid_mic_id': '40',
            'last_mic_id': '41',
            'net_percent_change': '42',
            'regular_market_percent_change': '43',
            'mark_price_net_change': '44',
            'mark_price_percent_change': '45',
            'hard_to_borrow_quantity': '46',
            'hard_to_borrow_rate': '47',
            'hard_to_borrow': '48',
            'shortable': '49',
            'post_market_net_change': '50',
            'post_market_percent_change': '51'
        }
    
    def _get_next_request_id(self) -> str:
        self.request_id += 1
        return str(self.request_id)
    
    def _create_login_request(self) -> Dict:
        """Create LOGIN request for Schwab Streamer"""
        return {
            "requestid": self._get_next_request_id(),
            "service": "ADMIN",
            "command": "LOGIN",
            "SchwabClientCustomerId": self.schwab_client_customer_id,
            "SchwabClientCorrelId": self.schwab_client_correl_id,
            "parameters": {
                "Authorization": self.access_token,
                "SchwabClientChannel": self.schwab_client_channel,
                "SchwabClientFunctionId": self.schwab_client_function_id
            }
        }
    
    def _create_subscription_request(self, service: str, symbols: List[str], fields: List[str] = None) -> Dict:
        """Create subscription request for market data"""
        if fields is None:
            # Default fields for LEVELONE_EQUITIES
            fields = ['0', '1', '2', '3', '4', '5', '8', '10', '11', '12', '17', '18', '32', '34', '35']
        
        return {
            "requestid": self._get_next_request_id(),
            "service": service,
            "command": "SUBS",
            "SchwabClientCustomerId": self.schwab_client_customer_id,
            "SchwabClientCorrelId": self.schwab_client_correl_id,
            "parameters": {
                "keys": ",".join(symbols),
                "fields": ",".join(fields)
            }
        }
    
    def _create_logout_request(self) -> Dict:
        """Create LOGOUT request"""
        return {
            "requestid": self._get_next_request_id(),
            "service": "ADMIN",
            "command": "LOGOUT",
            "SchwabClientCustomerId": self.schwab_client_customer_id,
            "SchwabClientCorrelId": self.schwab_client_correl_id,
            "parameters": {}
        }
    
    async def connect(self) -> bool:
        """Connect to Schwab Streamer WebSocket"""
        try:
            logger.info("Connecting to Schwab Streamer...")
            self.websocket = await websockets.connect(self.streamer_url)
            self.connected = True
            
            # Send login request
            login_request = self._create_login_request()
            await self.websocket.send(json.dumps({"requests": [login_request]}))
            
            # Wait for login response
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if 'response' in response_data:
                for resp in response_data['response']:
                    if resp.get('command') == 'LOGIN':
                        if resp['content']['code'] == 0:
                            logger.info("Successfully logged into Schwab Streamer")
                            return True
                        else:
                            logger.error(f"Login failed: {resp['content']['msg']}")
                            return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to Schwab Streamer: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Schwab Streamer"""
        if self.websocket and self.connected:
            try:
                logout_request = self._create_logout_request()
                await self.websocket.send(json.dumps({"requests": [logout_request]}))
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
            finally:
                self.connected = False
                self.websocket = None
    
    async def subscribe_to_symbols(self, symbols: List[str], callback: Callable[[MarketData], None] = None):
        """Subscribe to real-time data for symbols"""
        if not self.connected:
            if not await self.connect():
                return False
        
        try:
            # Subscribe to LEVELONE_EQUITIES
            sub_request = self._create_subscription_request("LEVELONE_EQUITIES", symbols)
            await self.websocket.send(json.dumps({"requests": [sub_request]}))
            
            # Store callback for each symbol
            for symbol in symbols:
                self.data_callbacks[symbol.upper()] = callback
            
            logger.info(f"Subscribed to symbols: {symbols}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to symbols: {e}")
            return False
    
    def _parse_equity_data(self, content: Dict) -> MarketData:
        """Parse LEVELONE_EQUITIES data into MarketData object"""
        try:
            symbol = content.get('key', '')
            last_price = content.get('3', 0)  # Last Price
            bid_price = content.get('1', last_price)  # Bid Price
            ask_price = content.get('2', last_price)  # Ask Price
            volume = content.get('8', 0)  # Total Volume
            high = content.get('10', last_price)  # High Price
            low = content.get('11', last_price)  # Low Price
            open_price = content.get('17', last_price)  # Open Price
            close_price = content.get('12', last_price)  # Close Price
            net_change = content.get('18', 0)  # Net Change
            net_percent_change = content.get('42', 0)  # Net Percent Change
            
            # Parse timestamp
            quote_time = content.get('34', 0)  # Quote Time
            if quote_time:
                timestamp = datetime.fromtimestamp(quote_time / 1000)
            else:
                timestamp = datetime.now()
            
            return MarketData(
                symbol=symbol,
                price=last_price,
                bid=bid_price,
                ask=ask_price,
                volume=volume,
                timestamp=timestamp,
                change=net_change,
                change_percent=net_percent_change,
                high=high,
                low=low,
                open=open_price,
                previous_close=close_price,
                provider=self.name
            )
        except Exception as e:
            logger.error(f"Error parsing equity data: {e}")
            return None
    
    async def start_streaming(self):
        """Start listening for streaming data"""
        if not self.connected:
            logger.error("Not connected to Schwab Streamer")
            return
        
        try:
            logger.info("Starting Schwab Streamer data stream...")
            
            while self.connected:
                try:
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    
                    # Handle different message types
                    if 'data' in data:
                        await self._handle_data_message(data['data'])
                    elif 'notify' in data:
                        await self._handle_notify_message(data['notify'])
                    elif 'response' in data:
                        await self._handle_response_message(data['response'])
                        
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    break
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
            
        except Exception as e:
            logger.error(f"Error in streaming loop: {e}")
        finally:
            self.connected = False
    
    async def _handle_data_message(self, data_messages: List[Dict]):
        """Handle data messages from streamer"""
        for message in data_messages:
            if message.get('service') == 'LEVELONE_EQUITIES':
                for content in message.get('content', []):
                    market_data = self._parse_equity_data(content)
                    if market_data:
                        symbol = market_data.symbol
                        if symbol in self.data_callbacks and self.data_callbacks[symbol]:
                            try:
                                await self.data_callbacks[symbol](market_data)
                            except Exception as e:
                                logger.error(f"Error in data callback for {symbol}: {e}")
    
    async def _handle_notify_message(self, notify_messages: List[Dict]):
        """Handle notify messages (heartbeats)"""
        for message in notify_messages:
            if 'heartbeat' in message:
                # Call heartbeat callbacks
                for callback in self.heartbeat_callbacks:
                    try:
                        await callback(message['heartbeat'])
                    except Exception as e:
                        logger.error(f"Error in heartbeat callback: {e}")
    
    async def _handle_response_message(self, response_messages: List[Dict]):
        """Handle response messages"""
        for message in response_messages:
            command = message.get('command', '')
            code = message.get('content', {}).get('code', -1)
            
            if command == 'SUBS' and code == 0:
                logger.info("Subscription successful")
            elif command == 'SUBS' and code != 0:
                logger.error(f"Subscription failed: {message.get('content', {}).get('msg', 'Unknown error')}")
    
    async def get_quote(self, symbol: str) -> Optional[MarketData]:
        """Get current quote for a symbol"""
        # If we have streaming data, return the latest
        if symbol.upper() in self.subscriptions:
            return self.subscriptions[symbol.upper()]
        
        # For non-streaming, we'd need to implement Schwab REST API calls
        logger.warning(f"No streaming data available for {symbol}")
        return None
    
    async def get_historical_data(self, symbol: str, period: str = "1d", interval: str = "1m") -> Optional[pd.DataFrame]:
        """Get historical data - would need Schwab REST API implementation"""
        logger.warning("Historical data requires Schwab REST API implementation")
        return None
    
    async def get_option_chain(self, symbol: str) -> Optional[Dict]:
        """Get option chain - would need Schwab REST API implementation"""
        logger.warning("Option chain requires Schwab REST API implementation")
        return None
    
    async def get_market_hours(self) -> Optional[Dict]:
        """Get market hours - would need Schwab REST API implementation"""
        logger.warning("Market hours requires Schwab REST API implementation")
        return None

class PureStockDataProvider(BaseDataProvider):
    def __init__(self, api_key: str):
        self.name = "pure_stock_data"
        self.api_key = api_key
        self.base_url = "https://api.purestockdata.com"
    
    async def get_quote(self, symbol: str) -> Optional[MarketData]:
        # Implementation for Pure Stock Data API
        # This would be similar to yfinance but using their API
        pass
    
    async def get_historical_data(self, symbol: str, period: str = "1d", interval: str = "1m") -> Optional[pd.DataFrame]:
        # Implementation for historical data
        pass
    
    async def get_option_chain(self, symbol: str) -> Optional[Dict]:
        # Implementation for option chains
        pass
    
    async def get_market_hours(self) -> Optional[Dict]:
        # Implementation for market hours
        pass

class DataProviderManager:
    def __init__(self, provider_type: DataProviderType = DataProviderType.SCHWAB, **kwargs):
        self.provider_type = provider_type
        self.provider = self._create_provider(provider_type, **kwargs)
    
    def _create_provider(self, provider_type: DataProviderType, **kwargs) -> BaseDataProvider:
        if provider_type == DataProviderType.SCHWAB:
            return SchwabStreamerProvider(**kwargs)
        elif provider_type == DataProviderType.PURE_STOCK_DATA:
            return PureStockDataProvider(**kwargs)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
    
    async def get_quote(self, symbol: str) -> Optional[MarketData]:
        return await self.provider.get_quote(symbol)
    
    async def get_historical_data(self, symbol: str, period: str = "1d", interval: str = "1m") -> Optional[pd.DataFrame]:
        return await self.provider.get_historical_data(symbol, period, interval)
    
    async def get_option_chain(self, symbol: str) -> Optional[Dict]:
        return await self.provider.get_option_chain(symbol)
    
    async def get_market_hours(self) -> Optional[Dict]:
        return await self.provider.get_market_hours()
    
    async def subscribe_to_symbols(self, symbols: List[str], callback: Callable[[MarketData], None] = None):
        """Subscribe to real-time data (only works with Schwab Streamer)"""
        if isinstance(self.provider, SchwabStreamerProvider):
            return await self.provider.subscribe_to_symbols(symbols, callback)
        else:
            logger.warning("Real-time subscription only available with Schwab Streamer")
            return False
    
    async def start_streaming(self):
        """Start streaming data (only works with Schwab Streamer)"""
        if isinstance(self.provider, SchwabStreamerProvider):
            await self.provider.start_streaming()
        else:
            logger.warning("Streaming only available with Schwab Streamer")
    
    async def disconnect(self):
        """Disconnect from provider"""
        if hasattr(self.provider, 'disconnect'):
            await self.provider.disconnect()

# For backward compatibility and simple usage
def get_provider(provider_type: str = "schwab", **kwargs):
    """Get a data provider instance"""
    if provider_type.lower() == "schwab":
        provider_enum = DataProviderType.SCHWAB
    elif provider_type.lower() == "pure_stock_data":
        provider_enum = DataProviderType.PURE_STOCK_DATA
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
    
    return DataProviderManager(provider_enum, **kwargs)

# Example usage
if __name__ == "__main__":
    async def test_schwab():
        # This would require actual Schwab credentials
        data_provider = DataProviderManager(DataProviderType.SCHWAB,
                                          access_token="your_access_token",
                                          schwab_client_customer_id="your_customer_id")
        
        # Test quote
        quote = await data_provider.get_quote("SPY")
        print(f"Quote: {quote}")
        
        # Test streaming
        await data_provider.subscribe_to_symbols(["SPY"])
        await data_provider.start_streaming()
    
    # asyncio.run(test_schwab()) 