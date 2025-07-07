"""
Data Provider Abstraction Layer
Allows easy switching between different data sources (yfinance, Schwab, pure stock data)
"""

import os
import asyncio
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import yfinance as yf
from database import log_event


class DataProvider(ABC):
    """Abstract base class for data providers."""
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get historical OHLCV data for a symbol and timeframe."""
        pass
    
    @abstractmethod
    async def get_latest_price(self, symbol: str) -> float:
        """Get the latest price for a symbol."""
        pass
    
    @abstractmethod
    async def get_ohlcv_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Get OHLCV data for a symbol and timeframe."""
        pass
    
    @abstractmethod
    async def get_atr(self, symbol: str, timeframe: str, period: int = 14) -> float:
        """Calculate ATR for a symbol and timeframe."""
        pass
    
    @abstractmethod
    async def get_ema(self, symbol: str, timeframe: str, period: int) -> float:
        """Calculate EMA for a symbol and timeframe."""
        pass
    
    @abstractmethod
    async def get_sma(self, symbol: str, timeframe: str, period: int) -> float:
        """Calculate SMA for a symbol and timeframe."""
        pass


class YFinanceProvider(DataProvider):
    """YFinance data provider implementation."""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 60  # Cache for 60 seconds
    
    def _get_yf_interval(self, timeframe: str) -> str:
        """Convert timeframe to yfinance interval."""
        mapping = {
            "1m": "1m",
            "3m": "3m", 
            "5m": "5m",
            "10m": "10m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "1d": "1d",
            "1w": "1wk",
            "scalp": "1m",
            "day": "1d",
            "multiday": "1d",
            "swing": "1d",
            "position": "1d",
            "long_term": "1wk"
        }
        return mapping.get(timeframe, "1d")
    
    async def get_historical_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get historical data from yfinance."""
        try:
            interval = self._get_yf_interval(timeframe)
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if data.empty:
                await log_event("yfinance_no_data", {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "start_date": start_date,
                    "end_date": end_date
                })
                return pd.DataFrame()
            
            # Standardize column names
            data.columns = [col.lower() for col in data.columns]
            data = data.reset_index()
            data['date'] = data['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            await log_event("yfinance_data_loaded", {
                "symbol": symbol,
                "timeframe": timeframe,
                "rows": len(data)
            })
            
            return data
            
        except Exception as e:
            await log_event("yfinance_error", {
                "symbol": symbol,
                "timeframe": timeframe,
                "error": str(e)
            })
            return pd.DataFrame()
    
    async def get_latest_price(self, symbol: str) -> float:
        """Get latest price from yfinance."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return info.get('regularMarketPrice', 0.0)
        except Exception as e:
            await log_event("yfinance_price_error", {"symbol": symbol, "error": str(e)})
            return 0.0
    
    async def get_ohlcv_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Get recent OHLCV data."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=limit * 2)  # Get extra data for calculations
        
        data = await self.get_historical_data(symbol, timeframe, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        
        if not data.empty:
            return data.tail(limit)
        return pd.DataFrame()
    
    async def get_atr(self, symbol: str, timeframe: str, period: int = 14) -> float:
        """Calculate ATR using yfinance data."""
        try:
            data = await self.get_ohlcv_data(symbol, timeframe, period + 20)
            
            if len(data) < period:
                return 0.0
            
            # Calculate True Range
            data['high_low'] = data['high'] - data['low']
            data['high_close'] = abs(data['high'] - data['close'].shift())
            data['low_close'] = abs(data['low'] - data['close'].shift())
            data['true_range'] = data[['high_low', 'high_close', 'low_close']].max(axis=1)
            
            # Calculate ATR
            atr = data['true_range'].rolling(window=period).mean().iloc[-1]
            return float(atr) if not pd.isna(atr) else 0.0
            
        except Exception as e:
            await log_event("atr_calculation_error", {
                "symbol": symbol,
                "timeframe": timeframe,
                "error": str(e)
            })
            return 0.0
    
    async def get_ema(self, symbol: str, timeframe: str, period: int) -> float:
        """Calculate EMA using yfinance data."""
        try:
            data = await self.get_ohlcv_data(symbol, timeframe, period + 20)
            
            if len(data) < period:
                return 0.0
            
            # Calculate EMA
            ema = data['close'].ewm(span=period).mean().iloc[-1]
            return float(ema) if not pd.isna(ema) else 0.0
            
        except Exception as e:
            await log_event("ema_calculation_error", {
                "symbol": symbol,
                "timeframe": timeframe,
                "period": period,
                "error": str(e)
            })
            return 0.0
    
    async def get_sma(self, symbol: str, timeframe: str, period: int) -> float:
        """Calculate SMA using yfinance data."""
        try:
            data = await self.get_ohlcv_data(symbol, timeframe, period + 10)
            
            if len(data) < period:
                return 0.0
            
            # Calculate SMA
            sma = data['close'].rolling(window=period).mean().iloc[-1]
            return float(sma) if not pd.isna(sma) else 0.0
            
        except Exception as e:
            await log_event("sma_calculation_error", {
                "symbol": symbol,
                "timeframe": timeframe,
                "period": period,
                "error": str(e)
            })
            return 0.0


class SchwabProvider(DataProvider):
    """Schwab data provider implementation (placeholder for future)."""
    
    def __init__(self):
        # TODO: Implement Schwab API integration
        self.api_key = os.getenv("SCHWAB_API_KEY")
        self.api_secret = os.getenv("SCHWAB_API_SECRET")
    
    async def get_historical_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get historical data from Schwab (placeholder)."""
        await log_event("schwab_not_implemented", {
            "message": "Schwab provider not yet implemented",
            "symbol": symbol,
            "timeframe": timeframe
        })
        return pd.DataFrame()
    
    async def get_latest_price(self, symbol: str) -> float:
        """Get latest price from Schwab (placeholder)."""
        await log_event("schwab_not_implemented", {"message": "Schwab provider not yet implemented"})
        return 0.0
    
    async def get_ohlcv_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Get OHLCV data from Schwab (placeholder)."""
        await log_event("schwab_not_implemented", {"message": "Schwab provider not yet implemented"})
        return pd.DataFrame()
    
    async def get_atr(self, symbol: str, timeframe: str, period: int = 14) -> float:
        """Calculate ATR using Schwab data (placeholder)."""
        await log_event("schwab_not_implemented", {"message": "Schwab provider not yet implemented"})
        return 0.0
    
    async def get_ema(self, symbol: str, timeframe: str, period: int) -> float:
        """Calculate EMA using Schwab data (placeholder)."""
        await log_event("schwab_not_implemented", {"message": "Schwab provider not yet implemented"})
        return 0.0
    
    async def get_sma(self, symbol: str, timeframe: str, period: int) -> float:
        """Calculate SMA using Schwab data (placeholder)."""
        await log_event("schwab_not_implemented", {"message": "Schwab provider not yet implemented"})
        return 0.0


class PureStockDataProvider(DataProvider):
    """Pure stock data provider implementation (placeholder for future)."""
    
    def __init__(self):
        # TODO: Implement pure stock data integration
        self.data_source = os.getenv("PURE_STOCK_DATA_SOURCE")
    
    async def get_historical_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get historical data from pure stock data source (placeholder)."""
        await log_event("pure_stock_not_implemented", {
            "message": "Pure stock data provider not yet implemented",
            "symbol": symbol,
            "timeframe": timeframe
        })
        return pd.DataFrame()
    
    async def get_latest_price(self, symbol: str) -> float:
        """Get latest price from pure stock data (placeholder)."""
        await log_event("pure_stock_not_implemented", {"message": "Pure stock data provider not yet implemented"})
        return 0.0
    
    async def get_ohlcv_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Get OHLCV data from pure stock data (placeholder)."""
        await log_event("pure_stock_not_implemented", {"message": "Pure stock data provider not yet implemented"})
        return pd.DataFrame()
    
    async def get_atr(self, symbol: str, timeframe: str, period: int = 14) -> float:
        """Calculate ATR using pure stock data (placeholder)."""
        await log_event("pure_stock_not_implemented", {"message": "Pure stock data provider not yet implemented"})
        return 0.0
    
    async def get_ema(self, symbol: str, timeframe: str, period: int) -> float:
        """Calculate EMA using pure stock data (placeholder)."""
        await log_event("pure_stock_not_implemented", {"message": "Pure stock data provider not yet implemented"})
        return 0.0
    
    async def get_sma(self, symbol: str, timeframe: str, period: int) -> float:
        """Calculate SMA using pure stock data (placeholder)."""
        await log_event("pure_stock_not_implemented", {"message": "Pure stock data provider not yet implemented"})
        return 0.0


def get_data_provider() -> DataProvider:
    """Factory function to get the configured data provider."""
    provider = os.getenv("DATA_PROVIDER", "yfinance").lower()
    
    if provider == "yfinance":
        return YFinanceProvider()
    elif provider == "schwab":
        return SchwabProvider()
    elif provider == "pure_stock":
        return PureStockDataProvider()
    else:
        # Log event asynchronously if needed
        asyncio.create_task(log_event("unknown_data_provider", {
            "provider": provider,
            "falling_back_to": "yfinance"
        }))
        return YFinanceProvider()


# Global provider instance
_data_provider = None

def get_provider() -> DataProvider:
    """Get the global data provider instance."""
    global _data_provider
    if _data_provider is None:
        _data_provider = get_data_provider()
    return _data_provider 