# Development Practices

This document defines a lightweight, pragmatic set of practices for the Collexa PoC and beyond. It aims to keep velocity high while maintaining quality, security, and maintainability.

## Tech stack
- Frontend: Next.js (TypeScript, App Router)
- Backend: Python FastAPI
- Data: Postgres (with RLS), Vector DB, Object Storage
- Protocols: MCP, A2A, REST/OpenAPI
- Billing: Stripe

## Branching, commits, and PRs
- Create feature branches from main: `feat/<scope>-<short-name>` (e.g., `feat/ui-playground`)
- Small, focused PRs (ideally < 400 LOC); draft early for feedback
- Conventional Commits for all merges:
  - `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `build:`, `perf:`
- Require:
  - Green CI (lint, type check, unit tests)
  - At least one review approval
  - PR description with context and testing notes

## Coding standards
- Frontend (Next.js/TypeScript)
  - TypeScript strict mode; prefer explicit types at API boundaries
  - ESLint + Prettier; no linter warnings on merge
  - Component co-location with feature (see folder-structure.md)
- Backend (Python/FastAPI)
  - Python 3.11+
  - Ruff (lint), Black (format), mypy (type check, "strict-ish")
  - Pydantic models for request/response schemas
  - Dependency injection for services where appropriate

## Testing
- Frontend
  - Unit: Jest + React Testing Library (RTL)
  - E2E (optional in Phase 1): Playwright for core flows (create agent, invoke)
- Backend
  - Unit: pytest
  - Contract: schemathesis against OpenAPI (as time allows)
- Coverage targets (initial):
  - Frontend units ≥ 60%; Backend units ≥ 70%
- Fast local commands (examples; adapt to repo scripts):
  - Frontend: `npm test` (Jest), `npm run lint`, `npm run typecheck`
  - Backend: `pytest -q`, `ruff check .`, `black --check .`, `mypy app`

## API design
- OpenAPI-first. Version paths under `/v1`.
- Avoid breaking changes; add new fields as optional.
- Provide typed clients for the UI via openapi-typescript.
- Prefer SSE for streaming logs; use WebSockets for duplex interactions.

## Security and privacy
- Phase 1 baseline (must-have):
  - AuthN/AuthZ: accounts & sessions, JWT with `org_id` claim
  - Tenant isolation: Postgres RLS keyed by `org_id`
  - Per-agent API keys: hashed at rest, scoped to capabilities
  - HTTPS-only, strict CORS, CSRF for UI, rate limiting
  - Audit logging: actor_id, org_id, endpoint, agent_id, capability, status
- Phase 2 advanced:
  - OPA/Rego policies for tool/data access and budgets (RBAC/ABAC)
  - SSO (SAML/OIDC), SCIM, advanced audit/retention
  - Signed manifests/provenance, key rotation (KMS)

## Data and migrations
- Use Alembic for DB migrations; one revision per change
- Backward-compatible migrations; include downgrade where feasible
- Review migrations for RLS policy impacts and long-running locks

## Observability
- Structured logs everywhere (JSON preferred) with request_id and org_id
- Tracing (OpenTelemetry) for API → builder → runtime critical paths
- Metrics: invocation count, latency p50/p95, errors, cost tokens/cents
- Log redaction rules for PII and secrets

## Billing
- Stripe customer per org on signup
- Meter executions (invokes) and learning (evals/storage/tuning)
- Webhooks: verify signatures; idempotent handlers
- Reconcile usage to invoices daily; alert on anomalies

## Code review checklist (use as PR template)
- Tests: unit updated/added; coverage not regressing
- Errors: explicit error handling; no silent failures
- Security: authN/Z enforced; RLS respected; secrets not logged
- Privacy: PII masked/redacted; scopes least-privileged
- Performance: no obvious N+1; streaming where needed; pagination
- Observability: logs, metrics, traces where appropriate
- Docs: README/docs updated (endpoints, flows, configs)

## Documentation & diagrams
- Keep README and docs/ up to date when interfaces or flows change
- Architecture: docs/architecture.mmd (Mermaid)
- PoC acceptance: docs/poc-checklist.md

## Developer experience
- Make local setup easy: one script to start DB + API + UI in dev
- Use fixtures/factories for tests; seed data for common flows
- Prefer smaller modules and functions; keep files short and focused

## Frontend specifics
- State: prefer React Query for server state; avoid global state unless necessary
- API calls: centralize in a /lib/api client generated from OpenAPI
- Accessibility: basic a11y checks and semantic HTML
- Avoid flaky e2e tests; mark with @flaky and stabilize later

## Backend specifics
- Routers organized by domain; Pydantic schemas colocated under `schemas/`
- Services pure and testable; repositories encapsulate DB access
- Background jobs via queue/workflow engine; avoid long-running HTTP requests
- Rate limits and input validation on public endpoints

## Versioning & deprecation
- Introduce new major versions only when necessary; support N and N-1 for clients
- Announce deprecations in README and changelog with timelines

## Secrets and configuration
- Never commit secrets; use env vars and secret managers in CI/CD
- Separate dev/test/prod configs; sensible defaults checked into repo

## Fail fast, iterate
- Prefer shipping the smallest useful slice with observability, then iterate
- Timebox spikes; document findings in docs/notes if useful

