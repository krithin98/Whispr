# Vomy & iVomy Rule Architecture

## Overview

The Vomy & iVomy rule system captures **volatility unwind patterns** based on EMA (Exponential Moving Average) crossovers across different candle timeframes. These rules identify high-conviction reversal signals that occur when multiple EMAs align in specific patterns.

## Key Concepts

### Vomy (Bearish Unwind)
- **Pattern**: `ema8 < ema13 < ema21 < ema48`
- **Signal**: Bearish reversal from uptrend
- **Description**: Fast EMA (8) crosses below Pullback EMA (13), then Pivot EMA (21), then Slow EMA (48)

### iVomy (Bullish Unwind)
- **Pattern**: `ema8 > ema13 > ema21 > ema48`
- **Signal**: Bullish reversal from downtrend
- **Description**: Fast EMA (8) crosses above Pullback EMA (13), then Pivot EMA (21), then Slow EMA (48)

## Supported Timeframes

The system supports 12 candle timeframes, each with different sensitivity and noise characteristics:

| Timeframe | Sensitivity | Noise Level | ATR Period | Use Case |
|-----------|-------------|-------------|------------|----------|
| 1m        | very_high   | high        | scalp      | Scalping |
| 3m        | high        | high        | scalp      | Scalping |
| 5m        | high        | medium      | scalp      | Day trading |
| 10m       | medium_high | medium      | scalp      | Day trading |
| 15m       | medium_high | medium      | scalp      | Swing trading |
| 30m       | medium      | low         | scalp      | Swing trading |
| 1h        | medium      | low         | day        | Swing trading |
| 2h        | medium_low  | low         | day        | Position trading |
| 4h        | medium_low  | very_low    | day        | Position trading |
| 1d        | low         | very_low    | multiday   | Long-term |
| 1w        | very_low    | very_low    | swing      | Long-term |
| 1M        | very_low    | very_low    | position   | Long-term |

## EMA Periods

The system uses four key EMA periods:
- **Fast EMA**: 8 periods
- **Pullback EMA**: 13 periods  
- **Pivot EMA**: 21 periods
- **Slow EMA**: 48 periods

## Rule Generation

### Total Rules Generated
- **24 total rules** (2 rules × 12 timeframes)
- **12 Vomy rules** (bearish unwind)
- **12 iVomy rules** (bullish unwind)

### Rule Naming Convention
- `Vomy {timeframe} Trigger` (e.g., "Vomy 1h Trigger")
- `Ivomy {timeframe} Trigger` (e.g., "Ivomy 5m Trigger")

### Rule Properties
- **Priority**: 7 (high-conviction signals)
- **Signal Type**: reversal
- **Tags**: `["vomy/ivomy", "{timeframe}", "trigger"]`
- **Enabled**: true

## Implementation Architecture

### 1. Configuration (`vomy_rule_specification.json`)
- Defines supported timeframes and metadata
- Specifies EMA periods and rule expressions
- Contains timeframe sensitivity and noise levels

### 2. Rule Generator (`vomy_rules.py`)
- `VomyRuleGenerator`: Creates rules for all timeframes
- `VomyRuleEvaluator`: Evaluates rules against EMA data
- Supports filtering by timeframe, type, and direction

### 3. Integration with Rules Engine
- Rules are stored in database with `rule_type = 'vomy_ivomy'`
- Evaluated during tick processing
- Triggers logged as events for analytics

### 4. API Endpoints
- `POST /rules/generate-vomy`: Generate all Vomy/iVomy rules
- `GET /rules/vomy`: List all Vomy/iVomy rules
- `GET /rules/vomy/{timeframe}`: Get rules by timeframe
- `GET /rules/vomy/type/{rule_type}`: Get rules by type
- `GET /analytics/vomy`: Get trigger statistics
- `GET /vomy/specification`: Get configuration
- `GET /vomy/timeframes`: Get timeframe metadata

## Usage Examples

### Rule Generation
```python
from vomy_rules import VomyRuleGenerator

generator = VomyRuleGenerator()
rules = generator.generate_all_rules()
print(f"Generated {len(rules)} rules")
```

### Rule Evaluation
```python
from vomy_rules import VomyRuleEvaluator

evaluator = VomyRuleEvaluator()
evaluator.update_ema_values("1h", {
    "ema8": 102.1,
    "ema13": 102.3, 
    "ema21": 102.5,
    "ema48": 102.8
})

triggered = evaluator.evaluate_rules(rules)
```

### API Usage
```bash
# Generate rules
curl -X POST http://localhost:8000/rules/generate-vomy

# Get all Vomy rules
curl http://localhost:8000/rules/vomy

# Get rules for specific timeframe
curl http://localhost:8000/rules/vomy/1h

# Get analytics
curl http://localhost:8000/analytics/vomy
```

## Pattern Recognition

### Vomy Pattern (Bearish)
```
EMA Values: ema8=100.0, ema13=100.2, ema21=100.4, ema48=100.6
Pattern: ema8 < ema13 < ema21 < ema48 ✓
Result: Vomy trigger (bearish reversal)
```

### iVomy Pattern (Bullish)
```
EMA Values: ema8=101.0, ema13=100.8, ema21=100.6, ema48=100.4
Pattern: ema8 > ema13 > ema21 > ema48 ✓
Result: iVomy trigger (bullish reversal)
```

### No Pattern (Mixed)
```
EMA Values: ema8=100.5, ema13=100.3, ema21=100.7, ema48=100.1
Pattern: Mixed signals ✗
Result: No trigger
```

## Timeframe Selection Guidelines

### High-Frequency Trading (1m-5m)
- **Pros**: High sensitivity, quick signals
- **Cons**: High noise, false signals
- **Best for**: Scalping with tight risk management

### Day Trading (10m-1h)
- **Pros**: Balanced sensitivity and noise
- **Cons**: Moderate signal frequency
- **Best for**: Day trading with swing positions

### Position Trading (4h-1d)
- **Pros**: Clean signals, low noise
- **Cons**: Lower sensitivity, slower signals
- **Best for**: Position trading and trend following

### Long-Term Trading (1w-1M)
- **Pros**: Very clean signals, major trend changes
- **Cons**: Very low sensitivity, rare signals
- **Best for**: Long-term portfolio management

## Integration with Other Systems

### Golden Gate System
- Vomy/iVomy rules complement Golden Gate ATR-based rules
- Golden Gate: ATR level-based entries
- Vomy/iVomy: EMA crossover-based reversals

### ATR Rule System
- ATR rules: Multi-level ATR-based entries
- Vomy/iVomy: Volatility unwind patterns
- Can be used together for comprehensive analysis

### Event Logging
- Triggers logged as `vomy_rule_trigger` events
- Includes EMA values, timeframe, and direction
- Enables historical analysis and backtesting

## Testing

Run the test suite to verify functionality:
```bash
cd backend
python3 test_vomy_rules.py
```

The test suite demonstrates:
- Rule generation for all timeframes
- Pattern evaluation with sample data
- API endpoint functionality
- Timeframe sensitivity analysis

## Future Enhancements

1. **Dynamic EMA Periods**: Allow configurable EMA periods per timeframe
2. **Confirmation Filters**: Add volume or momentum confirmations
3. **Risk Management**: Integrate with position sizing rules
4. **Backtesting**: Historical performance analysis
5. **Machine Learning**: Pattern recognition improvements

## Conclusion

The Vomy & iVomy rule system provides a robust framework for identifying volatility unwind patterns across multiple timeframes. By combining EMA crossover logic with timeframe-specific sensitivity, it offers traders a comprehensive tool for capturing reversal opportunities in various market conditions. 