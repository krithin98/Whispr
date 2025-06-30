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

## API Endpoints

- `GET /` - Health check
- `GET /last_events?limit=5` - View recent database events
- `GET /costs` - Compare LLM costs across providers
- `GET /rules` - View all active rules
- `WS /ws/ticks` - Real-time tick stream with AI suggestions

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