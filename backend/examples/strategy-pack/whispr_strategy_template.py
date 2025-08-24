from typing import Iterable
from dataclasses import dataclass
from backend.strategies.contracts import Strategy, MarketEvent, Signal

@dataclass
class TemplateStrategy:
    name: str = "template"
    version: str = "0.1.0"

    def on_event(self, event: MarketEvent) -> Iterable[Signal]:
        """Process market events and emit signals."""
        if event.kind == "internal" and event.payload.get("gg_cross_38"):
            yield Signal(
                ts=event.ts, 
                symbol=event.symbol, 
                name="GG_trigger", 
                strength=0.7,
                meta={"strategy": self.name, "version": self.version}
            )
        
        # Example: emit signal on price crosses
        if event.kind == "tick" and event.payload.get("price_cross_ema"):
            yield Signal(
                ts=event.ts,
                symbol=event.symbol,
                name="price_cross_ema",
                strength=0.5,
                meta={"strategy": self.name, "ema_type": "13"}
            )
