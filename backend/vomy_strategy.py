"""
Vomy & iVomy Strategy Generator
Generates volatility unwind strategies based on EMA crossovers across different candle timeframes.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

class VomyStrategyGenerator:
    """Generates Vomy and iVomy strategies for volatility unwind patterns."""
    
    def __init__(self, config_path: str = "data/vomy_rule_specification.json"):
        """Initialize the Vomy strategy generator with configuration."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.strategies = []
        
    def _load_config(self) -> Dict[str, Any]:
        """Load the Vomy strategy configuration."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Vomy strategy configuration not found at {self.config_path}")
    
    def generate_all_strategies(self) -> List[Dict[str, Any]]:
        """Generate all Vomy and iVomy strategies for all supported timeframes."""
        self.strategies = []
        
        for timeframe in self.config["supported_candle_timeframes"]:
            # Generate Vomy strategy (bearish unwind)
            vomy_strategy = self._generate_strategy("vomy", timeframe)
            self.strategies.append(vomy_strategy)
            
            # Generate iVomy strategy (bullish unwind)
            ivomy_strategy = self._generate_strategy("ivomy", timeframe)
            self.strategies.append(ivomy_strategy)
        
        return self.strategies
    
    def _generate_strategy(self, strategy_type: str, timeframe: str) -> Dict[str, Any]:
        """Generate a single Vomy or iVomy strategy for a specific timeframe."""
        strategy_def = self.config["rule_definitions"][strategy_type]
        timeframe_meta = self.config["timeframe_metadata"][timeframe]
        
        # Generate strategy name
        name = f"{strategy_type.capitalize()} {timeframe} Trigger"
        
        # Generate description
        description = f"{strategy_def['description']} on {timeframe} timeframe"
        
        # Generate tags
        tags = [strategy_def["tags"][0], timeframe, "trigger"]
        
        # Create strategy object
        strategy = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "expression": strategy_def["expression"],
            "tags": tags,
            "priority": strategy_def["priority"],
            "enabled": strategy_def["enabled"],
            "strategy_type": "vomy_ivomy",
            "timeframe": timeframe,
            "signal_type": strategy_def["signal_type"],
            "direction": strategy_def["direction"],
            "ema_periods": self.config["ema_periods"],
            "timeframe_metadata": timeframe_meta,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        return strategy
    
    def get_strategies_by_timeframe(self, timeframe: str) -> List[Dict[str, Any]]:
        """Get all Vomy and iVomy strategies for a specific timeframe."""
        return [strategy for strategy in self.strategies if strategy["timeframe"] == timeframe]
    
    def get_strategies_by_type(self, strategy_type: str) -> List[Dict[str, Any]]:
        """Get all strategies of a specific type (vomy or ivomy)."""
        return [strategy for strategy in self.strategies if strategy["name"].lower().startswith(strategy_type)]
    
    def get_strategies_by_direction(self, direction: str) -> List[Dict[str, Any]]:
        """Get all strategies by direction (bullish or bearish)."""
        return [strategy for strategy in self.strategies if strategy["direction"] == direction]
    
    def get_strategy_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific strategy by name."""
        for strategy in self.strategies:
            if strategy["name"] == name:
                return strategy
        return None
    
    def get_supported_timeframes(self) -> List[str]:
        """Get list of supported candle timeframes."""
        return self.config["supported_candle_timeframes"]
    
    def get_ema_periods(self) -> Dict[str, int]:
        """Get the EMA periods used in Vomy strategies."""
        return self.config["ema_periods"]
    
    def get_timeframe_metadata(self, timeframe: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific timeframe."""
        return self.config["timeframe_metadata"].get(timeframe)
    
    def export_strategies_to_json(self, filepath: str = None) -> str:
        """Export generated strategies to JSON file."""
        if filepath is None:
            filepath = f"data/generated_vomy_strategies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "total_strategies": len(self.strategies),
                "strategy_types": ["vomy", "ivomy"],
                "timeframes": self.get_supported_timeframes()
            },
            "strategies": self.strategies
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return filepath
    
    def get_strategy_statistics(self) -> Dict[str, Any]:
        """Get statistics about generated strategies."""
        stats = {
            "total_strategies": len(self.strategies),
            "by_type": {
                "vomy": len(self.get_strategies_by_type("vomy")),
                "ivomy": len(self.get_strategies_by_type("ivomy"))
            },
            "by_direction": {
                "bullish": len(self.get_strategies_by_direction("bullish")),
                "bearish": len(self.get_strategies_by_direction("bearish"))
            },
            "by_timeframe": {}
        }
        
        for timeframe in self.get_supported_timeframes():
            stats["by_timeframe"][timeframe] = len(self.get_strategies_by_timeframe(timeframe))
        
        return stats


class VomyStrategyEvaluator:
    """Evaluates Vomy and iVomy strategies based on EMA values."""
    
    def __init__(self):
        """Initialize the Vomy strategy evaluator."""
        self.ema_values = {}
        self.triggered_strategies = []
        
    def update_ema_values(self, timeframe: str, ema_values: Dict[str, float]):
        """Update EMA values for a specific timeframe."""
        self.ema_values[timeframe] = ema_values
    
    def evaluate_strategies(self, strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate a list of Vomy/iVomy strategies against current EMA values."""
        triggered = []
        
        for strategy in strategies:
            if not strategy["enabled"]:
                continue
                
            timeframe = strategy["timeframe"]
            if timeframe not in self.ema_values:
                continue
            
            ema_data = self.ema_values[timeframe]
            
            # Check if we have all required EMA values
            required_emas = ["ema8", "ema13", "ema21", "ema48"]
            if not all(ema in ema_data for ema in required_emas):
                continue
            
            # Evaluate the strategy expression
            is_triggered = self._evaluate_expression(strategy["expression"], ema_data)
            
            if is_triggered:
                trigger_event = {
                    "strategy_id": strategy["id"],
                    "strategy_name": strategy["name"],
                    "timeframe": timeframe,
                    "triggered_at": datetime.utcnow().isoformat(),
                    "ema_values": ema_data,
                    "signal_type": strategy["signal_type"],
                    "direction": strategy["direction"]
                }
                triggered.append(trigger_event)
                self.triggered_strategies.append(trigger_event)
        
        return triggered
    
    def _evaluate_expression(self, expression: str, ema_values: Dict[str, float]) -> bool:
        """Evaluate a strategy expression using current EMA values."""
        try:
            # Create a safe evaluation environment
            local_vars = ema_values.copy()
            
            # Replace EMA references with actual values
            for ema_name, value in ema_values.items():
                local_vars[ema_name] = value
            
            # Evaluate the expression
            result = eval(expression, {"__builtins__": {}}, local_vars)
            return bool(result)
            
        except Exception as e:
            print(f"Error evaluating expression '{expression}': {e}")
            return False
    
    def get_triggered_strategies(self) -> List[Dict[str, Any]]:
        """Get all triggered strategies."""
        return self.triggered_strategies
    
    def clear_triggered_strategies(self):
        """Clear the list of triggered strategies."""
        self.triggered_strategies = []
    
    def get_ema_values(self, timeframe: str) -> Optional[Dict[str, float]]:
        """Get current EMA values for a timeframe."""
        return self.ema_values.get(timeframe)


# Backward compatibility aliases
VomyStrategyGenerator = VomyStrategyGenerator
VomyStrategyEvaluator = VomyStrategyEvaluator


# Example usage and testing
if __name__ == "__main__":
    # Initialize generator
    generator = VomyStrategyGenerator()
    
    # Generate all strategies
    strategies = generator.generate_all_strategies()
    
    # Print statistics
    stats = generator.get_strategy_statistics()
    print("Vomy & iVomy Strategy Statistics:")
    print(json.dumps(stats, indent=2))
    
    # Print sample strategies
    print(f"\nGenerated {len(strategies)} strategies:")
    for strategy in strategies[:4]:  # Show first 4 strategies
        print(f"- {strategy['name']}: {strategy['description']}")
    
    # Export strategies
    export_path = generator.export_strategies_to_json()
    print(f"\nStrategies exported to: {export_path}") 