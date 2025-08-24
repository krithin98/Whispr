import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.strategies.registry import load_strategies, get_strategy_names
from backend.strategies.contracts import Strategy, MarketEvent, Signal

def test_registry_loads():
    """Test that the strategy registry loads without crashing."""
    # This will load zero or template strategies; just assert no crash + type seam intact
    strategies = list(get_strategy_names())
    print(f"Available strategies: {strategies}")
    
    # Test loading strategies (may be empty if no packages installed)
    loaded_strategies = list(load_strategies())
    print(f"Loaded strategies: {len(loaded_strategies)}")
    
    # Verify type seam is intact
    for strategy in loaded_strategies:
        assert hasattr(strategy, 'name'), "Strategy must have name attribute"
        assert hasattr(strategy, 'version'), "Strategy must have version attribute"
        assert hasattr(strategy, 'on_event'), "Strategy must have on_event method"
        assert callable(strategy.on_event), "Strategy.on_event must be callable"

def test_market_event_creation():
    """Test that MarketEvent can be created and used."""
    event = MarketEvent(
        ts=1234567890.0,
        symbol="SPX",
        kind="tick",
        payload={"price": 4500.0, "volume": 1000}
    )
    
    assert event.ts == 1234567890.0
    assert event.symbol == "SPX"
    assert event.kind == "tick"
    assert event.payload["price"] == 4500.0

def test_signal_creation():
    """Test that Signal can be created and used."""
    signal = Signal(
        ts=1234567890.0,
        symbol="SPX",
        name="test_signal",
        strength=0.8,
        meta={"test": True}
    )
    
    assert signal.ts == 1234567890.0
    assert signal.symbol == "SPX"
    assert signal.name == "test_signal"
    assert signal.strength == 0.8
    assert signal.meta["test"] is True

if __name__ == "__main__":
    print("🧪 Testing Strategy Registry Extensibility...")
    
    test_market_event_creation()
    test_signal_creation()
    test_registry_loads()
    
    print("✅ All strategy registry tests passed!")
    print("🎯 Extensibility seam is working correctly!")
