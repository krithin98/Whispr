# Unused Strategies

This folder contains strategies that are **NOT** part of the core ATR level tracking system.

## Moved Strategies

### Non-ATR Strategies (Isolated)
- `conviction_arrow_strategy.py` - Hourly conviction arrow signals from Pivot Ribbon indicator
- `four_h_po_dot_strategy.py` - 4H PO Dot signals from Phase Oscillator indicator  
- `vomy_strategy.py` - Volatility unwind strategies based on EMA crossovers
- `test_four_h_po_dot_strategy.py` - Tests for PO Dot strategy
- `test_vomy_strategy.py` - Tests for Vomy strategy

### Deprecated ATR Implementation
- `fib_level_strategy_old.py` - Old broken Fibonacci level strategy (replaced by `fixed_fib_level_strategy.py`)

## Why These Were Moved

The primary focus is now on **SPX ATR Level Tracking** with:
- Real-time level hit detection
- Level-to-level movement analysis  
- Golden Gate sequence tracking (.382 → .618)
- Comprehensive level hit database storage

These unused strategies can be restored later if needed, but for now they clutter the core ATR system.

## Core ATR Files (Kept Active)
- `atr_strategy.py` - Core ATR calculations
- `fixed_fib_level_strategy.py` - Working Fibonacci level tracking
- `atr_system.py` - Main orchestration system
- `test_atr_strategy.py` - ATR strategy tests

## Restore Instructions

To restore any strategy:
```bash
mv unused_strategies/[strategy_name].py ./
```
