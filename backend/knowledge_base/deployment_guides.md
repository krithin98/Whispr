# Deployment Guides

## Targets
- Local (uvicorn), Container (Docker), CI/CD (GitHub Actions).

## Config
- Env vars only; provide `.env.example`.
- No secrets in repo; use secrets manager/CI vars.

## Health & Readiness
- `/health` and `/ready` endpoints.
- Container liveness/restart policy.

## CI/CD
- Build → test → package → deploy.
- Block deploys on failing tests.
- Tag images by git SHA.

## Rollback
- Keep last N images; document & test rollback steps.

## Observability
- Structured logs + basic metrics.
- Error alerts with rate thresholds.

## Acceptance Checks
- [ ] Reproducible build artifact.
- [ ] Versioned deploys with rollback.
- [ ] Config documented; secrets safe.
