# Seer Trading Copilot

A real-time trading copilot built with FastAPI, Docker, and AI integration for automated strategy execution and signal generation.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+

### Running the Application
```bash
# Clone the repository
git clone <repository-url>
cd seer

# Start the services
docker-compose up -d

# Access the API
curl http://localhost:8000/docs
```

## 📊 Strategy Systems

The system implements 5 core trading strategies:

1. **ATR Level/Multi-Level Strategy** - ATR-based entry signals
2. **Vomy/iVomy Strategy** - EMA crossover signals  
3. **4H PO Dot Strategy** - Phase Oscillator bullish crosses on 4H SPX
4. **Hourly Conviction Arrow Strategy** - EMA crossovers on 1H timeframe
5. **Golden Gate Strategy** - ATR level timing signals

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Indicators    │    │   Strategies    │    │   Rules Engine  │
│                 │    │                 │    │                 │
│ • ThinkScript   │───▶│ • ATR Strategy  │    │ • Future Logic  │
│ • Pine Script   │    │ • Vomy Strategy │    │ • Non-Indicator │
│ • Custom Logic  │    │ • PO Dot        │    │   Based Rules   │
└─────────────────┘    │ • Conviction    │    └─────────────────┘
                       │ • Golden Gate   │
                       └─────────────────┘
```

## 📁 Project Structure

```
seer/
├── backend/                    # FastAPI backend services
│   ├── main.py                # Main application
│   ├── strategies.py          # Strategy management
│   ├── indicators.py          # Indicator data consumption
│   ├── database.py            # Database operations
│   ├── *_strategy.py          # Individual strategy implementations
│   └── test_*.py              # Strategy test files
├── ui/                        # Next.js frontend (future)
├── services/                  # Microservices
│   └── rules_engine/          # Rules processing service
└── docker-compose.yml         # Service orchestration
```

## 🔌 API Endpoints

### Strategy Management
- `GET /strategies/` - List all strategies
- `POST /strategies/` - Create new strategy
- `GET /strategies/{id}` - Get specific strategy
- `PUT /strategies/{id}` - Update strategy
- `DELETE /strategies/{id}` - Delete strategy

### Strategy-Specific
- `GET /strategies/atr/` - ATR strategy data
- `GET /strategies/vomy/` - Vomy strategy data
- `GET /strategies/po-dot/` - PO Dot strategy data
- `GET /strategies/conviction-arrow/` - Conviction Arrow strategy data

### Testing
- `POST /test/atr-strategy` - Test ATR strategy
- `POST /test/vomy-strategy` - Test Vomy strategy
- `POST /test/po-dot-strategy` - Test PO Dot strategy
- `POST /test/conviction-arrow-strategy` - Test Conviction Arrow strategy

## 🧪 Testing

Run individual strategy tests:
```bash
cd backend
python test_atr_strategy.py
python test_vomy_strategy.py
python test_four_h_po_dot_strategy.py
```

## 📈 Development Status

✅ **Complete:**
- Strategy architecture and implementation
- API endpoints and testing
- Database schema and operations
- File organization and naming conventions

🔄 **In Progress:**
- UI development
- Real-time data integration

📋 **Planned:**
- Backtesting engine
- Portfolio management
- AI enhancement features

## 📚 Documentation

- [Development Log](DEVELOPMENT_LOG.md) - Detailed development history and next steps
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when running)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

[Add your license here]

---

**Note:** This is a trading system. Use at your own risk and always test thoroughly before live trading. 