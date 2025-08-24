# Strategy Development Guide

## 🚀 **Add Your Own Strategy in 5 Steps**

### **Step 1: Use the Template**
```bash
# Option A: Copy the example
cp -r examples/strategy-pack/ my-strategy/

# Option B: Use copier (if available)
pipx run copier gh:your-org/whispr-strategy-template my-strategy
```

### **Step 2: Implement Strategy.on_event(...)**
```python
from typing import Iterable
from backend.strategies.contracts import Strategy, MarketEvent, Signal

class MyStrategy:
    name: str = "my_strategy"
    version: str = "0.1.0"
    
    def on_event(self, event: MarketEvent) -> Iterable[Signal]:
        # Your logic here
        if event.kind == "tick" and self._should_trigger(event):
            yield Signal(
                ts=event.ts,
                symbol=event.symbol,
                name="my_signal",
                strength=0.8,
                meta={"strategy": self.name}
            )
    
    def _should_trigger(self, event: MarketEvent) -> bool:
        # Implement your trigger logic
        return event.payload.get("price", 0) > 1000
```

### **Step 3: Add Entry Point**
```toml
# pyproject.toml
[project.entry-points."whispr.strategies"]
my_strategy = "my_strategy_module:MyStrategy"
```

### **Step 4: Install Locally**
```bash
cd my-strategy/
pip install -e .
```

### **Step 5: Verify Discovery**
```bash
python -c "from backend.strategies.registry import load_strategies; print([s.name for s in load_strategies()])"
# Should show: ['template', 'my_strategy']
```

## 📋 **Strategy Contract Requirements**

### **MarketEvent Fields**
- `ts`: Unix timestamp (float)
- `symbol`: Trading symbol (str)
- `kind`: Event type - "tick", "bar", "internal", "news"
- `payload`: Dict with event-specific data

### **Signal Fields**
- `ts`: Unix timestamp (float)
- `symbol`: Trading symbol (str)
- `name`: Signal identifier (str)
- `strength`: Confidence 0.0-1.0 (float)
- `meta`: Optional metadata dict

### **Strategy Protocol**
- `name`: Strategy identifier
- `version`: Semantic version
- `on_event(event)`: Must yield Signal objects

## 🔧 **Testing Your Strategy**

### **Unit Test Example**
```python
import pytest
from backend.strategies.contracts import MarketEvent, Signal
from my_strategy import MyStrategy

def test_strategy_triggers_on_high_price():
    strategy = MyStrategy()
    event = MarketEvent(
        ts=1234567890.0,
        symbol="SPX",
        kind="tick",
        payload={"price": 5000.0}
    )
    
    signals = list(strategy.on_event(event))
    assert len(signals) == 1
    assert signals[0].name == "my_signal"
    assert signals[0].strength == 0.8
```

### **Integration Test**
```bash
# Test with the registry
python -c "
from backend.strategies.registry import load_strategies
strategies = list(load_strategies())
print(f'Loaded {len(strategies)} strategies:')
for s in strategies:
    print(f'  - {s.name} v{s.version}')
"
```

## 📊 **Performance Considerations**

### **Best Practices**
- Keep `on_event` fast (< 1ms per call)
- Use early returns for non-triggering events
- Cache expensive calculations
- Avoid external API calls in hot paths

### **Monitoring**
```python
import time

def on_event(self, event: MarketEvent) -> Iterable[Signal]:
    start = time.time()
    try:
        # Your logic here
        yield signal
    finally:
        duration = time.time() - start
        if duration > 0.001:  # Log slow strategies
            print(f"Warning: {self.name} took {duration*1000:.2f}ms")
```

## 🚨 **Common Pitfalls**

### **Avoid These Mistakes**
- **Heavy computation**: Don't do complex math in `on_event`
- **External calls**: No network requests in hot paths
- **State mutation**: Keep strategies stateless
- **Memory leaks**: Don't accumulate data indefinitely

### **Debugging Tips**
```python
# Add logging to your strategy
import logging

logger = logging.getLogger(__name__)

def on_event(self, event: MarketEvent) -> Iterable[Signal]:
    logger.debug(f"Processing {event.kind} for {event.symbol}")
    # ... your logic
```

## 📚 **Advanced Features**

### **Configuration**
```python
class ConfigurableStrategy:
    def __init__(self, threshold: float = 1000.0):
        self.threshold = threshold
    
    def on_event(self, event: MarketEvent) -> Iterable[Signal]:
        if event.payload.get("price", 0) > self.threshold:
            yield Signal(...)
```

### **State Management**
```python
class StatefulStrategy:
    def __init__(self):
        self.last_signal_time = 0
        self.min_interval = 60  # seconds
    
    def on_event(self, event: MarketEvent) -> Iterable[Signal]:
        if event.ts - self.last_signal_time < self.min_interval:
            return
        
        # Generate signal
        self.last_signal_time = event.ts
        yield Signal(...)
```

## 🔗 **Integration Points**

### **Rules Engine**
Strategies can be triggered by rules defined in YAML:
```yaml
name: "strategy_trigger"
inputs:
  timeframe: "1m"
  indicators: ["ATR", "EMA13"]
logic:
  - if: "strategy.my_strategy.triggered"
    then: ["alert:info:Strategy signal detected"]
```

### **Event Logging**
All strategy signals are automatically logged:
```python
# In your strategy
yield Signal(
    ts=event.ts,
    symbol=event.symbol,
    name="breakout_signal",
    strength=0.9,
    meta={
        "strategy": self.name,
        "breakout_level": event.payload.get("price"),
        "volume": event.payload.get("volume")
    }
)
```

## 📈 **Scaling Considerations**

### **Current Architecture**
- **Tier 0**: SQLite + in-process execution
- **Tier 1**: Postgres + Redis + worker processes
- **Tier 2**: Kafka + distributed workers + object storage

### **Migration Path**
- Start with simple strategies
- Add configuration as needed
- Implement performance monitoring
- Scale horizontally when required

## 🎯 **Next Steps**

1. **Start Simple**: Implement basic logic first
2. **Add Tests**: Ensure reliability
3. **Monitor Performance**: Watch execution times
4. **Iterate**: Refine based on real data
5. **Share**: Contribute back to the community

---

**Need Help?** Check the examples, run the tests, or ask in the community!

