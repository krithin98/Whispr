from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any

class DataProvider(ABC):
    """Abstract interface for streaming market data."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish any network connections or start background tasks."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Clean up resources before shutdown."""

    @abstractmethod
    async def subscribe(self) -> AsyncIterator[Dict[str, Any]]:
        """Yield tick data dictionaries indefinitely."""
        raise StopAsyncIteration
