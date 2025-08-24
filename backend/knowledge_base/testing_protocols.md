# Testing Protocols

## Pyramid
- Unit > Integration > E2E. Optimize for fast feedback.

## Unit Tests
- One behavior per test; arrange/act/assert; clear names.
- Prefer fakes over heavy mocks.

## Integration
- API routes via test client.
- DB via fixtures or temp DB.
- External services mocked.

## Regression
- For every bug: add failing test first.
- Keep `tests/regression/` for notable issues.

## Coverage & Perf
- Prioritize domain logic coverage.
- Micro-benchmarks for hot paths in `tests/perf/`.

## CI Hooks
- Run `black`, `isort`, `mypy`, `pytest -q`.

## Acceptance Checks
- [ ] New features include unit + route tests.
- [ ] Regressions have reproducible tests.
- [ ] Tests deterministic and isolated.
