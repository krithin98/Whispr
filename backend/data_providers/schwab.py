from __future__ import annotations

from typing import AsyncIterator, Dict, Any

from .base import DataProvider

try:  # Optional: external collector is heavy and may not be available during tests
    from whispr.backend.data_collector import SchwabDataCollector  # type: ignore
except Exception:  # pragma: no cover - collector may not exist in all envs
    SchwabDataCollector = None  # type: ignore


class SchwabProvider(DataProvider):
    """Data provider that proxies to the Schwab API collector."""

    def __init__(self, collector: "SchwabDataCollector") -> None:
        if SchwabDataCollector is None:
            raise ImportError("SchwabDataCollector is not available")
        self.collector = collector

    async def connect(self) -> None:
        await self.collector.connect()

    async def subscribe(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        async for tick in self.collector.stream_real_time([symbol]):
            yield {
                "symbol": tick.symbol,
                "price": tick.price,
                "high": tick.high,
                "low": tick.low,
                "volume": tick.volume,
                "timestamp": tick.timestamp.isoformat(),
            }

    async def disconnect(self) -> None:
        await self.collector.disconnect()
