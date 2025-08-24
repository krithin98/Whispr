# Whispr Trading System Architecture

## System Overview

Whispr is a modular, extensible trading system designed for clean architecture and scalability. The system follows hexagonal architecture principles with clear boundaries between domain logic, infrastructure, and external interfaces.

## Architecture Diagram

```mermaid
flowchart LR
  subgraph Frontend
    Codex[Codex Chat] --- Cursor[Cursor IDE]
  end

  subgraph App
    API[FastAPI]
    Engine[Rules Engine]
    Strat[Strategy Registry (entry_points)]
  end

  subgraph Data
    DB[(Postgres/SQLite)]
    OBJ[(Object Store)]
    MQ[(Redis/Kafka)]
  end

  Codex -->|compiled prompt| API
  Cursor -->|diffs/tests| API
  API --> Engine --> Strat
  Engine --> DB
  Engine --> MQ
  MQ --> Engine
  DB --> OBJ
```

## Core Components

### **API Layer (FastAPI)**
- RESTful endpoints for system interaction
- WebSocket support for real-time data
- Authentication and authorization
- Request/response validation with Pydantic

### **Rules Engine**
- YAML-based rule configuration
- JSON Schema validation
- Event-driven rule evaluation
- Support for complex trading logic

### **Strategy Registry**
- Plugin-based architecture using Python entry points
- Dynamic strategy loading
- Protocol-based contracts for extensibility
- Third-party strategy support

### **Data Layer**
- **Tier 0**: SQLite + in-process queues (development)
- **Tier 1**: Postgres + Redis queues (team/production)
- **Tier 2**: Postgres + read replicas + Kafka + object store (enterprise)

## Extensibility Points

### **Strategy Plugins**
Third parties can add strategies without touching core code:
```python
# In third-party package
from backend.strategies.contracts import Strategy, MarketEvent, Signal

class MyStrategy(Strategy):
    name = "my_strategy"
    version = "1.0.0"
    
    def on_event(self, event: MarketEvent) -> Iterable[Signal]:
        # Custom logic here
        pass
```

### **Rules as Configuration**
Users define trading logic in YAML:
```yaml
name: golden_gate_intraday
inputs:
  timeframe: "1m"
  indicators: ["ATR", "EMA13", "EMA48"]
logic:
  - if: "cross(atr.38, price)"
    then: ["emit:GG_trigger", "alert:info:GG crossed 38%"]
```

### **Event Contracts**
Stable data contracts for system integration:
- `MarketEvent`: Market data and internal events
- `Signal`: Strategy-generated trading signals
- `Alert`: System notifications and alerts

## Scaling Strategy

### **Horizontal Scaling**
- Stateless API workers
- Queue-based task processing
- Database read replicas
- Event streaming with Kafka

### **Vertical Scaling**
- Optimized database queries
- Efficient data structures
- Caching strategies
- Background task processing

## Security & Compliance

- Environment-based configuration
- Secrets management
- Role-based access control
- Audit logging
- Data encryption at rest and in transit

## Monitoring & Observability

- Structured logging with correlation IDs
- Health and readiness endpoints
- Performance metrics
- Distributed tracing
- Alert management

## Development Workflow

1. **Codex Integration**: AI-assisted development with specialized agents
2. **Testing**: Comprehensive test coverage with pytest
3. **CI/CD**: Automated quality gates and deployment
4. **Code Quality**: Black, isort, mypy enforcement

## Future Enhancements

- Machine learning integration
- Advanced backtesting
- Multi-asset support
- Real-time risk management
- Advanced analytics and reporting
