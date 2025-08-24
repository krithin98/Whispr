# Infrastructure Patterns

## IaC
- Prefer declarative (e.g., Terraform) when infra exists.
- Keep templates small and composable.

## Networking
- Least privilege for security groups.
- Timeouts/retries on outbound calls.

## Storage
- Backups with retention; test restores.
- Forward-only migrations or feature-gated.

## Scaling
- Stateless app containers; horizontal scale.
- Background workers for long tasks.

## Security
- No plaintext secrets; rotate regularly.
- Validate inputs at the edge; rate-limit sensitive endpoints.

## Acceptance Checks
- [ ] IaC reviewed & version-controlled.
- [ ] Least privilege verified.
- [ ] Backups/restores tested.
