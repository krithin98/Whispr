"""
Test script for Vomy & iVomy Strategy System
Demonstrates strategy generation, evaluation, and API functionality.
"""

import asyncio
import json
from datetime import datetime
from vomy_rules import VomyStrategyGenerator, VomyStrategyEvaluator

async def test_vomy_strategy_generation():
    """Test Vomy strategy generation."""
    print("=== Testing Vomy & iVomy Strategy Generation ===")
    
    # Initialize generator
    generator = VomyStrategyGenerator()
    
    # Generate all strategies
    strategies = generator.generate_all_strategies()
    
    print(f"Generated {len(strategies)} total strategies")
    
    # Get statistics
    stats = generator.get_strategy_statistics()
    print(f"Statistics: {json.dumps(stats, indent=2)}")
    
    # Show sample strategies
    print("\nSample Strategies:")
    for i, strategy in enumerate(strategies[:6]):  # Show first 6 strategies
        print(f"{i+1}. {strategy['name']}")
        print(f"   Description: {strategy['description']}")
        print(f"   Expression: {strategy['expression']}")
        print(f"   Tags: {strategy['tags']}")
        print(f"   Timeframe: {strategy['timeframe']}")
        print(f"   Direction: {strategy['direction']}")
        print()
    
    return strategies

def test_vomy_strategy_evaluation():
    """Test Vomy strategy evaluation with sample EMA data."""
    print("=== Testing Vomy & iVomy Strategy Evaluation ===")
    
    # Initialize evaluator
    evaluator = VomyStrategyEvaluator()
    
    # Sample EMA data for different timeframes
    sample_ema_data = {
        "3m": {
            "ema8": 100.5,
            "ema13": 100.3,
            "ema21": 100.1,
            "ema48": 99.8
        },
        "10m": {
            "ema8": 101.2,
            "ema13": 101.0,
            "ema21": 100.8,
            "ema48": 100.5
        },
        "1h": {
            "ema8": 102.1,
            "ema13": 102.3,
            "ema21": 102.5,
            "ema48": 102.8
        },
        "1d": {
            "ema8": 103.0,
            "ema13": 103.2,
            "ema21": 103.4,
            "ema48": 103.7
        }
    }
    
    # Update evaluator with EMA data
    for timeframe, ema_values in sample_ema_data.items():
        evaluator.update_ema_values(timeframe, ema_values)
        print(f"Updated {timeframe} EMA values: {ema_values}")
    
    # Generate test strategies
    generator = VomyStrategyGenerator()
    test_strategies = generator.generate_all_strategies()
    
    # Filter strategies for our test timeframes
    test_timeframes = ["3m", "10m", "1h", "1d"]
    filtered_strategies = [strategy for strategy in test_strategies if strategy["timeframe"] in test_timeframes]
    
    print(f"\nEvaluating {len(filtered_strategies)} strategies...")
    
    # Evaluate strategies
    triggered = evaluator.evaluate_strategies(filtered_strategies)
    
    print(f"Triggered {len(triggered)} strategies:")
    for trigger in triggered:
        print(f"- {trigger['strategy_name']}")
        print(f"  Timeframe: {trigger['timeframe']}")
        print(f"  Direction: {trigger['direction']}")
        print(f"  EMA Values: {trigger['ema_values']}")
        print()
    
    return triggered

async def test_api_endpoints():
    """Test the API endpoints for Vomy strategies."""
    print("=== Testing Vomy API Endpoints ===")
    
    import httpx
    
    # Base URL for the API
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        try:
            # Test specification endpoint
            print("Testing /vomy/specification...")
            response = await client.get(f"{base_url}/vomy/specification")
            if response.status_code == 200:
                spec = response.json()
                print(f"✓ Specification loaded successfully")
                print(f"  Supported timeframes: {len(spec['supported_timeframes'])}")
                print(f"  EMA periods: {spec['ema_periods']}")
            else:
                print(f"✗ Failed to load specification: {response.status_code}")
            
            # Test timeframes endpoint
            print("\nTesting /vomy/timeframes...")
            response = await client.get(f"{base_url}/vomy/timeframes")
            if response.status_code == 200:
                timeframes = response.json()
                print(f"✓ Timeframes loaded successfully")
                print(f"  Available timeframes: {list(timeframes.keys())}")
            else:
                print(f"✗ Failed to load timeframes: {response.status_code}")
            
            # Test strategy generation endpoint
            print("\nTesting /strategies/generate-vomy...")
            response = await client.post(f"{base_url}/strategies/generate-vomy")
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Strategies generated successfully")
                print(f"  Total strategies: {result.get('total_strategies', 0)}")
                print(f"  Saved strategies: {result.get('saved_strategies', 0)}")
            else:
                print(f"✗ Failed to generate strategies: {response.status_code}")
            
            # Test strategies listing endpoint
            print("\nTesting /strategies/vomy...")
            response = await client.get(f"{base_url}/strategies/vomy")
            if response.status_code == 200:
                strategies = response.json()
                print(f"✓ Strategies loaded successfully")
                print(f"  Total strategies in database: {len(strategies)}")
                
                # Show sample strategies
                for strategy in strategies[:3]:
                    print(f"  - {strategy['name']} (Priority: {strategy['priority']})")
            else:
                print(f"✗ Failed to load strategies: {response.status_code}")
            
        except Exception as e:
            print(f"✗ API test failed: {str(e)}")

def demonstrate_ema_crossover_patterns():
    """Demonstrate different EMA crossover patterns that trigger Vomy/iVomy strategies."""
    print("=== EMA Crossover Pattern Examples ===")
    
    # Initialize evaluator
    evaluator = VomyStrategyEvaluator()
    
    # Example 1: Vomy pattern (bearish unwind)
    print("\nExample 1: Vomy Pattern (Bearish Unwind)")
    vomy_emas = {
        "ema8": 100.0,   # Fast EMA
        "ema13": 100.2,  # Pullback EMA
        "ema21": 100.4,  # Pivot EMA
        "ema48": 100.6   # Slow EMA
    }
    print(f"EMA Values: {vomy_emas}")
    print("Pattern: ema8 < ema13 < ema21 < ema48")
    print("Result: Vomy trigger (bearish reversal)")
    
    # Example 2: iVomy pattern (bullish unwind)
    print("\nExample 2: iVomy Pattern (Bullish Unwind)")
    ivomy_emas = {
        "ema8": 101.0,   # Fast EMA
        "ema13": 100.8,  # Pullback EMA
        "ema21": 100.6,  # Pivot EMA
        "ema48": 100.4   # Slow EMA
    }
    print(f"EMA Values: {ivomy_emas}")
    print("Pattern: ema8 > ema13 > ema21 > ema48")
    print("Result: iVomy trigger (bullish reversal)")
    
    # Example 3: No pattern (mixed signals)
    print("\nExample 3: No Pattern (Mixed Signals)")
    mixed_emas = {
        "ema8": 100.5,   # Fast EMA
        "ema13": 100.3,  # Pullback EMA
        "ema21": 100.7,  # Pivot EMA
        "ema48": 100.1   # Slow EMA
    }
    print(f"EMA Values: {mixed_emas}")
    print("Pattern: Mixed (no clear trend)")
    print("Result: No trigger")

def show_timeframe_sensitivity():
    """Show how different timeframes affect Vomy/iVomy sensitivity."""
    print("=== Timeframe Sensitivity Analysis ===")
    
    generator = VomyStrategyGenerator()
    
    print("\nTimeframe Sensitivity Levels:")
    for timeframe in ["3m", "10m", "30m", "1h", "4h", "1d", "1w"]:
        metadata = generator.get_timeframe_metadata(timeframe)
        if metadata:
            print(f"{timeframe:>4}: Sensitivity={metadata['sensitivity']:>12}, Noise={metadata['noise_level']:>10}")
        else:
            print(f"{timeframe:>4}: Not supported")
    
    print("\nKey Insights:")
    print("- Lower timeframes (3m, 10m) have higher sensitivity but more noise")
    print("- Higher timeframes (4h, 1d, 1w) have lower sensitivity but cleaner signals")
    print("- Vomy/iVomy patterns are most reliable on 30m-1h timeframes")

async def main():
    """Run all tests."""
    print("Vomy & iVomy Strategy System Test Suite")
    print("=" * 50)
    
    # Test strategy generation
    strategies = await test_vomy_strategy_generation()
    
    # Test strategy evaluation
    triggered = test_vomy_strategy_evaluation()
    
    # Demonstrate patterns
    demonstrate_ema_crossover_patterns()
    
    # Show timeframe sensitivity
    show_timeframe_sensitivity()
    
    # Test API endpoints (if server is running)
    print("\n" + "=" * 50)
    print("API Testing (requires server to be running)")
    await test_api_endpoints()
    
    print("\n" + "=" * 50)
    print("Test Suite Complete!")
    print(f"Generated {len(strategies)} strategies")
    print(f"Triggered {len(triggered)} strategies in evaluation")

if __name__ == "__main__":
    asyncio.run(main()) 
