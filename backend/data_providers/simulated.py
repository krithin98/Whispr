import asyncio
from typing import AsyncIterator, Dict, Any

from .base import DataProvider

class SimulatedProvider(DataProvider):
    """Simple tick generator for local development and testing."""

    def __init__(self) -> None:
        self._tick = 0
        self._running = False

    async def connect(self) -> None:
        self._running = True

    async def disconnect(self) -> None:
        self._running = False

    async def subscribe(self) -> AsyncIterator[Dict[str, Any]]:
        while self._running:
            tick_data = {"tick": self._tick, "value": 100 + self._tick}
            self._tick += 1
            yield tick_data
            await asyncio.sleep(1)
