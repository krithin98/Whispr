# Seer – MVP Step 1, 2 & 3

## Quick start

```bash
cp env.example .env
# Add your GROQ_API_KEY to .env (get free credits at https://console.groq.com)
docker compose up --build
```

Open http://localhost:8000 for a health-check and test the WebSocket at ws://localhost:8000/ws/ticks.

## Features

- ✅ **Step 1**: FastAPI with WebSocket tick streaming
- ✅ **Step 2**: SQLite journaling with persistent database
- ✅ **Step 3**: Rule engine with AI suggestions
- ✅ **Cost-effective LLM**: Groq Llama-3 8B integration (10-20x cheaper than GPT-4o)
- ✅ **Week 1**: Schwab data feed integration + dry-run trade logging

## API Endpoints

- `GET /` - Health check
- `GET /last_events?limit=5` - View recent database events
- `GET /costs` - Compare LLM costs across providers
- `GET /rules` - View all active rules
- `WS /ws/ticks` - Real-time tick stream with AI suggestions
- `POST /trades` - Place simulated trade
- `GET /trades/open` - Get open trades
- `GET /trades/closed` - Get closed trades
- `POST /trades/{id}/close` - Close trade
- `GET /trades/performance` - Get performance metrics

## WebSocket Messages

### Tick Data
```json
{"tick": 5, "value": 105}
```

### AI Suggestions (when rules trigger)
```json
{
  "type": "suggestion",
  "rule_id": 1,
  "rule_name": "High price ping",
  "prompt": "Price crossed 105. Any risk-reducing actions?",
  "response": "Consider taking profits or setting stop-loss...",
  "cost": 0.000123,
  "model": "groq/llama3-8b-8192",
  "tick_data": {"tick": 5, "value": 105}
}
```

## Default Rules

The system comes with 3 test rules:
1. **High price ping**: Triggers when `value >= 105`
2. **Low price alert**: Triggers when `value <= 95`
3. **Tick milestone**: Triggers every 10 ticks

## LLM Configuration

**Default (Cost-effective)**: Groq Llama-3 8B
- Input: $0.05/1M tokens
- Output: $0.08/1M tokens
- Latency: ~40ms

**Easy upgrade path**: Change `LLM_PROVIDER=openai` and `LLM_MODEL=gpt-4o-mini` in `.env`

## Week 1 Implementation: Real Data + Trade Logging

### Data Feed Integration
- **Schwab Simulation**: Realistic market data patterns with volatility
- **Configurable**: Switch between simulated and real data via `USE_REAL_DATA`
- **Symbol Support**: Trade any symbol (default: SPY)

### Dry-Run Trade Logger
- **Simulated Trades**: Track P&L without risking real money
- **Performance Metrics**: Win rate, total P&L, max win/loss
- **Trade History**: Complete audit trail of all trades
- **Live Mode Ready**: Easy switch to real trading later

### Environment Configuration
```bash
# Data Feed
USE_REAL_DATA=false          # Set to true for real Schwab data
TRADING_SYMBOL=SPY          # Trading symbol

# Trading Mode
LIVE_TRADING=false          # Set to true for real orders
```

## Cost Comparison

| Model | Input Cost | Output Cost | vs Groq 8B |
|-------|------------|-------------|------------|
| Groq Llama-3 8B | $0.05/1M | $0.08/1M | baseline |
| OpenAI GPT-4o mini | $0.15/1M | $0.60/1M | 3-8x higher |
| OpenAI GPT-4o | $2.50/1M | $10.00/1M | 50-125x higher |

## Testing

1. **Start the app**: `docker compose up --build`
2. **Connect WebSocket**: You'll see ticks and AI suggestions when rules trigger
3. **Check events**: `curl http://localhost:8000/last_events?limit=10`
4. **View rules**: `curl http://localhost:8000/rules`
5. **Monitor costs**: `curl http://localhost:8000/costs`
6. **Test trades**: `curl -X POST 'http://localhost:8000/trades?symbol=SPY&side=buy&quantity=100&price=450.50'`
7. **Check performance**: `curl http://localhost:8000/trades/performance`
8. **Run Week 1 test**: `python test_week1.py` 