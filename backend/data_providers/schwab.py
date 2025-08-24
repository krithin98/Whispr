from typing import AsyncIterator, Dict, Any

from .base import DataProvider

class SchwabProvider(DataProvider):
    """Placeholder for future Schwab brokerage integration."""

    async def connect(self) -> None:
        raise NotImplementedError("SchwabProvider.connect is not implemented")

    async def disconnect(self) -> None:
        pass

    async def subscribe(self) -> AsyncIterator[Dict[str, Any]]:
        raise NotImplementedError("SchwabProvider.subscribe is not implemented")
