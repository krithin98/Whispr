from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any


class DataProvider(ABC):
    """Abstract interface for market data providers."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the underlying data source."""

    @abstractmethod
    async def subscribe(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        """Yield tick data for the given symbol."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the data source."""
