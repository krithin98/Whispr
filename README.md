# 6-Week Seer Co-pilot

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

3. **Start the application**
   ```bash
   docker compose up --build
   ```

4. **Verify it's working**
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