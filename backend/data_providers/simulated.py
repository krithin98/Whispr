from __future__ import annotations

import asyncio
from typing import AsyncIterator, Dict, Any

from .base import DataProvider


class SimulatedProvider(DataProvider):
    """Simple in-memory tick simulator used for development."""

    def __init__(self, delay: float = 1.0) -> None:
        self.delay = delay
        self._running = False

    async def connect(self) -> None:
        self._running = True

    async def subscribe(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        tick = 0
        while self._running:
            yield {"symbol": symbol, "tick": tick, "value": 100 + tick}
            tick += 1
            await asyncio.sleep(self.delay)

    async def disconnect(self) -> None:
        self._running = False
