# 6-Week Whispr Co-pilot

A real-time decision copilot that captures live context, applies user-defined rules, and surfaces AI-ranked suggestions in real-time.

## Project Overview

This is a 6-week MVP to prove the core loop: **data → rule → AI prompt → suggestion**

### Week 1 Deliverables ✅
- [x] FastAPI server running in Docker
- [x] WebSocket endpoint `/ws/ticks` streaming simulated tick JSON once per second
- [x] Health-check GET `/` returns status

## Quick Start

### Prerequisites
- Docker Desktop
- Python 3.11+
- Git

### Setup
1. **Clone and navigate to project**
   ```bash
   cd /Users/krith/tradingATR.ai
   ```

2. **Copy environment file** (optional for Week 1)
   ```bash
   cp env.example .env
   # Add your OPENAI_API_KEY when ready for Week 3
   ```

3. **Install frontend dependencies**
   ```bash
   npm --prefix whispr/ui install
   ```

4. **Start the application**
   ```bash
   docker compose up --build
   ```

5. **Verify it's working**
   - Health check: http://localhost:8000/
   - API docs: http://localhost:8000/docs
   - WebSocket: ws://localhost:8000/ws/ticks

## API Endpoints

### Health Check
```bash
GET /
```
Returns service status and active WebSocket connections.

### WebSocket Tick Stream
```bash
ws://localhost:8000/ws/ticks
```
Streams simulated SPX tick data every second:
```json
{
  "type": "tick",
  "data": {
    "timestamp": "2025-01-27T10:30:00.123456",
    "symbol": "SPX",
    "price": 4505.23,
    "volume": 25000,
    "bid": 4505.13,
    "ask": 4505.33,
    "change": 5.23,
    "change_percent": 0.116,
    "tick_id": 1706362200123
  }
}
```

### Status
```bash
GET /api/status
```
Returns detailed service status and feature availability.

## Testing the WebSocket

You can test the WebSocket stream using a simple HTML page or tools like:

### Using curl (for connection test)
```bash
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==" http://localhost:8000/ws/ticks
```

### Using wscat (if installed)
```bash
npm install -g wscat
wscat -c ws://localhost:8000/ws/ticks
```

## Project Structure

```
tradingATR.ai/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
├── docker-compose.yml  # Multi-service orchestration
├── env.example         # Environment variables template
├── README.md           # This file
└── data/               # Persistent data (created by Docker)
```

## Development

### Local Development (without Docker)
```bash
pip install -r requirements.txt
python main.py
```

### Docker Development
```bash
# Build and run
docker compose up --build

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## Next Steps (Week 2)

- [ ] SQLite journaling with events table
- [ ] Persist all ticks & system events
- [ ] Write-ahead logging (WAL) enabled
- [ ] ENV flag DATABASE_URL for Postgres swap later

## Architecture

- **Backend**: FastAPI + Starlette WebSockets
- **Database**: SQLite (WAL) → Postgres ready
- **AI Worker**: OpenAI GPT-4o via LangChain (Week 3+)
- **Overlay**: Tauri (Rust + Svelte) (Week 5+)
- **DevOps**: Docker Compose; ENV secrets for keys

## License

MIT (placeholder)

# Whispr – MVP Step 1, 2 & 3

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

| Model              | Input Cost | Output Cost | vs Groq 8B     |
| ------------------ | ---------- | ----------- | -------------- |
| Groq Llama-3 8B    | $0.05/1M   | $0.08/1M    | baseline       |
| OpenAI GPT-4o mini | $0.15/1M   | $0.60/1M    | 3-8x higher    |
| OpenAI GPT-4o      | $2.50/1M   | $10.00/1M   | 50-125x higher |

## Testing

1. **Start the app**: `docker compose up --build`
2. **Connect WebSocket**: You'll see ticks and AI suggestions when rules trigger
3. **Check events**: `curl http://localhost:8000/last_events?limit=10`
4. **View rules**: `curl http://localhost:8000/rules`
5. **Monitor costs**: `curl http://localhost:8000/costs`
