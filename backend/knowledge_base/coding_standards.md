# Coding Standards

## Language & Style
- Python 3.11; type hints required.
- Enforce `black`, `isort`, `mypy` via pre-commit.
- Small, single-purpose functions; early returns.

## Testing
- Tests-first where feasible; otherwise add tests with changes.
- Unit: fast, isolated, no network/FS.
- Integration: mock external boundaries unless explicitly needed.

## Error Handling
- Never 500 for expected invalid inputs → raise typed errors → 4xx.
- Log with context (request_id); no secret leakage.
- Don't swallow exceptions; re-raise with context.

## Dependencies
- Prefer stdlib; any new dep needs a one-line rationale in PR.
- Pin versions; refresh periodically.

## Docs
- Docstrings with examples for public functions.
- Update `ARCHITECTURE.md` when moving modules.

## Acceptance Checks
- [ ] Lint/type/test pass.
- [ ] New code has tests + docstrings.
- [ ] Public APIs + error codes documented.
