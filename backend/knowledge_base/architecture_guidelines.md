# Architecture Guidelines

## Extensibility & Scale (at a glance)
- **Plugin seam:** 3rd parties ship strategies as packages exposing `whispr.strategies` entry points.
- **Rules as config:** User-editable YAML rules validated by JSON Schema; no code changes needed.
- **Event contracts:** Append-only `market_events` → `strategy_triggers` → `alerts`, versioned payloads.
- **Tiers:** T0 (SQLite+threads) → T1 (Postgres+Redis) → T2 (Kafka+workers+object store).
- **Ops posture:** Structured logs, /health, /ready, metrics for trigger rate & queue depth.

*References: Pragmatic Programmer (seams/orthogonality), Clean Architecture (ports/adapters), DDIA (contracts/events), Release It! (resilience), Accelerate (flow).*

## Goals
- Loosely coupled, highly cohesive modules.
- Explicit data flow; side effects only at the edges (API/DB).
- Prefer composition over inheritance.

## Module Boundaries
- **api/**: thin controllers + request/response models; no domain logic.
- **backend/**: domain logic (atr_system, rules_engine, strategy_triggers).
- **db/**: schema/migrations; repositories.
- **tests/**: fast unit tests by default; mark slow/integration.

## Patterns
- Ports & Adapters (Hexagonal).
- CQRS-lite for read-heavy endpoints when helpful.
- Idempotent handlers for retries.

## Data & Schema
- Stable surrogate keys (UUID/INTEGER).
- `created_at`/`updated_at`; avoid soft deletes unless needed.
- Events (triggers): immutable records + outcome table.

## Reliability & Perf
- Validate at the edge; return 4xx for client mistakes.
- Offload heavy work to background tasks.
- Micro-benchmarks for hot paths in `tests/perf/`.

## Observability
- Structured logs with `request_id`.
- Health/ready endpoints; counters for strategy triggers.

## Acceptance Checks
- [ ] No circular deps across modules.
- [ ] API thin; domain logic in backend modules.
- [ ] Migrations backward compatible or gated.
- [ ] Failure behavior covered by tests.
