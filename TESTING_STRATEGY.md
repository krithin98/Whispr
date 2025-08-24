# Testing Strategy

This repository previously contained several ad-hoc test scripts. The new
approach uses **pytest** to provide consistent, automated verification of core
functionality. The current focus is on two critical areas:

- **Database Initialization** – ensures that required tables are created when
  the application starts.
- **Backtesting Engine** – validates that the engine can pull historical data
  and run backtests against a seeded strategy.

## Running Tests

```bash
pytest tests/test_database.py whispr/test_backtesting.py
```

## Future Improvements

- Expand coverage to additional strategies and data providers.
- Add integration tests that exercise API endpoints.
- Include performance benchmarks for backtesting algorithms.

