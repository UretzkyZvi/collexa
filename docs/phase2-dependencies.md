# Phase 2 Dependencies & Library Recommendations

## Overview

This document identifies open-source libraries with permissive licenses (MIT, Apache 2.0, BSD) that can accelerate Phase 2 development. All recommendations align with our tech stack: Python FastAPI backend, Next.js/TypeScript frontend, PostgreSQL database.

## Quick Reference by Milestone

| Milestone | Key Libraries | Priority |
|-----------|---------------|----------|
| H (Interoperability) | modelcontextprotocol/python, python-jose, OpenTelemetry | High |
| I (Workspace UI) | TanStack Table/Query, Recharts, react-hook-form/zod | Medium |
| J (Security) | OPA + transitions, Authlib, structlog | High |
| K (Billing) | Celery/RQ, fastapi-limiter, Apprise | Medium |
| L (Reproducibility) | Temporal, Hydra, DeepDiff | Medium |
| M (Performance) | Locust, asyncpg, pybreaker | High |
| N (Sandbox) | testcontainers-python, Vault+hvac, MLflow | High |

---

## Milestone H — Interoperability Core

### MCP Protocol & WebSocket Handling
**modelcontextprotocol/python** ([GitHub](https://github.com/modelcontextprotocol/python))
- License: MIT
- Tasks: MCP server/client primitives, tool schemas, capability advertisement
- Integration: Medium (introduces MCP types/flows; fits FastAPI/Starlette)
- Risks: Rapidly evolving spec; keep pace with updates

**modelcontextprotocol/typescript** ([npm](https://www.npmjs.com/package/@modelcontextprotocol/sdk))
- License: MIT
- Tasks: Frontend MCP client integration, testing tool listing/invocation
- Integration: Low–Medium
- Risks: API churn; version alignment with Python SDK

### Digital Signatures & Manifest Signing
**python-jose** ([PyPI](https://pypi.org/project/python-jose/))
- License: MIT
- Tasks: Sign/verify A2A descriptors and manifests (JWS/JWT), key rotation
- Integration: Low
- Risks: Correct key management/algorithm selection (prefer Ed25519/ES256)

**cryptography (PyCA)** ([PyPI](https://pypi.org/project/cryptography/))
- License: Apache 2.0
- Tasks: Low-level signing (Ed25519/ECDSA), X.509 publishing for verifiers
- Integration: Low–Medium
- Risks: Careful key storage; platform wheels needed for some environments

### Agent Communication & Reputation
**NATS.io** ([nats.py](https://github.com/nats-io/nats.py), [nats.ws](https://github.com/nats-io/nats.ws))
- License: Apache 2.0
- Tasks: Lightweight pub/sub for cross-agent events, decoupled invocation
- Integration: Medium
- Risks: Operability of NATS cluster; choose if event bus is needed

**scikit-learn + river** ([sklearn](https://scikit-learn.org/), [river](https://riverml.xyz/))
- License: BSD-3-Clause (sklearn), MIT (river)
- Tasks: Reputation scoring from reliability/latency; online updates
- Integration: Low–Medium
- Risks: Fairness and gaming protection; define bounded features

**OpenTelemetry** ([opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python))
- License: Apache 2.0
- Tasks: Emit spans/metrics for cross-agent success/latency feeding reputation
- Integration: Medium
- Risks: Collector ops; sampling and cardinality controls

---

## Milestone I — Workspace UI & Organization Settings

### UI Components & Data Management
**TanStack Table + TanStack Query** ([table](https://tanstack.com/table), [query](https://tanstack.com/query))
- License: MIT
- Tasks: Advanced filtering/sorting/virtualization; server-driven queries
- Integration: Low–Medium
- Risks: Column definitions/row-model can be verbose

**Recharts** ([recharts](https://recharts.org/))
- License: MIT
- Tasks: Budget/usage charts; run metrics visualization
- Integration: Low
- Risks: Performance with large datasets; consider aggregation

**react-hook-form + zod** ([rhf](https://react-hook-form.com/), [zod](https://zod.dev/))
- License: MIT
- Tasks: Budget config forms; org settings; validation
- Integration: Low
- Risks: Syncing API error messages with schema validation

### Search & Notifications
**Fuse.js** ([GitHub](https://github.com/krisk/Fuse))
- License: Apache 2.0
- Tasks: Client-side fuzzy search; quick navigation
- Integration: Low
- Risks: Prefer server-side search for large datasets

**Apprise** ([GitHub](https://github.com/caronc/apprise))
- License: BSD-2-Clause
- Tasks: Multi-channel alerts (email/webhook/Slack) for budget events
- Integration: Low
- Risks: Rate limiting and idempotency for noisy events

---

## Milestone J — Advanced Security

### Policy Engines (RBAC/ABAC)
**Open Policy Agent (OPA)** ([GitHub](https://github.com/open-policy-agent/opa))
- License: Apache 2.0
- Tasks: ABAC decisions; policy bundles; pre-invoke checks
- Integration: Medium
- Risks: Policy authoring learning curve; bundle distribution

**Cerbos** ([GitHub](https://github.com/cerbos/cerbos))
- License: Apache 2.0
- Tasks: Fine-grained authZ (RBAC/ABAC) with versioned policies and audit
- Integration: Medium
- Risks: Operate a Cerbos PDP service; choose OPA vs. Cerbos

**Casbin/PyCasbin** ([GitHub](https://github.com/casbin/pycasbin))
- License: Apache 2.0
- Tasks: Lightweight RBAC/ABAC; model+policy files; Postgres adapters
- Integration: Low–Medium
- Risks: Less feature-rich than OPA/Cerbos for complex ABAC

### SSO & Authentication
**Authlib** ([GitHub](https://github.com/lepture/authlib))
- License: BSD
- Tasks: OIDC/OAuth2 providers, token verification and flow
- Integration: Medium
- Risks: Robust ACS and logout flows required

**python3-saml (OneLogin)** ([GitHub](https://github.com/onelogin/python3-saml))
- License: MIT
- Tasks: SAML SSO integration
- Integration: Medium
- Risks: SAML metadata/clock skew; robust ACS and logout flows

### Approval Workflows
**Temporal** ([GitHub](https://github.com/temporalio/temporal))
- License: MIT
- Tasks: Human-in-the-loop approvals; retry/idempotency; timeouts
- Integration: High (server + worker infra)
- Risks: Operational overhead; worth it for complex approvals

**transitions** ([GitHub](https://github.com/pytransitions/transitions))
- License: MIT
- Tasks: Lightweight approval state flows (requested→approved/denied)
- Integration: Low–Medium
- Risks: Manual persistence and audit hooks required

### Audit Logging
**structlog** ([GitHub](https://github.com/hynek/structlog))
- License: MIT
- Tasks: Structured audit logs with actor/org/decision/outcome
- Integration: Low
- Risks: Ensure log integrity and immutability where needed

---

## Milestone K — Billing & Budgets

### Usage Metering
**OpenMeter** ([GitHub](https://github.com/openmeterio/openmeter))
- License: Apache 2.0
- Tasks: Usage metering pipeline; emit events from runs; aggregation for billing
- Integration: Medium–High (Kafka/ClickHouse stack commonly)
- Risks: Infrastructure overhead; consider managed option

### Async Processing & Rate Limiting
**Celery** ([GitHub](https://github.com/celery/celery))
- License: BSD
- Tasks: Async processing of Stripe webhooks and metering
- Integration: Medium
- Risks: Operate worker/Redis; idempotency keys for webhooks

**fastapi-limiter** ([GitHub](https://github.com/long2ice/fastapi-limiter))
- License: MIT
- Tasks: Budget enforcement via rate/quotas per org/agent
- Integration: Low–Medium
- Risks: Precision of quotas vs. rate limits; time-window drift

### Scheduling & Alerts
**APScheduler** ([GitHub](https://github.com/agronholm/apscheduler))
- License: MIT
- Tasks: Scheduled budget checks and threshold alerts
- Integration: Low
- Risks: Scheduler persistence and HA (consider Temporal/cron jobs)

---

## Milestone L — Reproducibility & Signed Logs

### Deterministic Execution
**Temporal** ([GitHub](https://github.com/temporalio/temporal))
- License: MIT
- Tasks: Deterministic workflows; replay; failure semantics
- Integration: Medium–High
- Risks: Platform choice; best for determinism but heavier

**Hydra** ([GitHub](https://github.com/facebookresearch/hydra))
- License: MIT
- Tasks: Deterministic run config management (model params, prompts, tool versions)
- Integration: Low–Medium
- Risks: Config sprawl; enforce immutability for recorded runs

### Diff & Comparison Tools
**DeepDiff** ([GitHub](https://github.com/seperman/deepdiff))
- License: MIT
- Tasks: Structured diff for replay output comparisons
- Integration: Low
- Risks: Non-deterministic fields (timestamps) require redaction rules

**jsondiffpatch** ([GitHub](https://github.com/benjamine/jsondiffpatch))
- License: MIT
- Tasks: Frontend diff visualization for replay comparisons
- Integration: Low
- Risks: Large JSON performance; consider server-side diffing

### Provenance Tracking
**python-prov** ([GitHub](https://github.com/trungdong/prov))
- License: BSD
- Tasks: Provenance model for run artifacts and lineage
- Integration: Medium
- Risks: Additional metadata modeling and storage

---

## Milestone M — Performance & Reliability

### Load Testing
**Locust** ([GitHub](https://github.com/locustio/locust))
- License: MIT
- Tasks: Load testing single- and cross-agent paths; scripted user flows
- Integration: Low–Medium
- Risks: Needs headless runs in CI/CD; resource consumption during tests

### Database & HTTP Performance
**asyncpg** ([GitHub](https://github.com/MagicStack/asyncpg))
- License: BSD-3-Clause
- Tasks: High-performance Postgres with pooling
- Integration: Low–Medium
- Risks: Ensure compatibility with Windows dev environments

**httpx** ([GitHub](https://github.com/encode/httpx))
- License: BSD-3-Clause
- Tasks: Efficient upstream calls; keep-alive; timeouts
- Integration: Low
- Risks: Tune pool limits/timeouts for bursty workloads

### Caching & Circuit Breakers
**fastapi-cache2** ([GitHub](https://github.com/long2ice/fastapi-cache2))
- License: MIT
- Tasks: Caching hot descriptors/manifests; response caching
- Integration: Low
- Risks: Cache invalidation/expiry coherence

**pybreaker** ([GitHub](https://github.com/danielfm/pybreaker))
- License: MIT
- Tasks: Circuit breakers, timeouts, fallbacks for dependent agents/tools
- Integration: Low
- Risks: Properly define failure thresholds and reset strategy

---

## Milestone N — Agent Sandbox Environments

### Container Orchestration
**testcontainers-python** ([GitHub](https://github.com/testcontainers/testcontainers-python))
- License: MIT
- Tasks: Ephemeral sandbox containers for learning runs and integration tests
- Integration: Low–Medium
- Risks: Less control for long-lived sandboxes; best for ephemeral

**Docker SDK for Python** ([GitHub](https://github.com/docker/docker-py))
- License: Apache 2.0
- Tasks: Sandbox lifecycle (start/stop/reset); isolation modes; resource limits
- Integration: Medium
- Risks: Security profiles (seccomp/AppArmor) required

### Credential Management
**HashiCorp Vault + hvac** ([Vault](https://github.com/hashicorp/vault), [hvac](https://github.com/hvac-dev/hvac))
- License: MPL 2.0 (Vault), Apache 2.0 (hvac)
- Tasks: Secure credential storage/rotation; scoped secret_ref integration
- Integration: Medium
- Risks: Operate Vault; seal/unseal workflows; policy management

### Learning & Assessment
**DSPy** ([GitHub](https://github.com/stanfordnlp/dspy))
- License: Apache 2.0
- Tasks: Autonomous learning loops (prompt optimization, tool refinement)
- Integration: Medium
- Risks: GPU/LLM cost controls; define guardrails to prevent drift

**MLflow** ([GitHub](https://github.com/mlflow/mlflow))
- License: Apache 2.0
- Tasks: Track learning progress/metrics; artifacts; run lineage; dashboards
- Integration: Medium
- Risks: Operate tracking server; storage backend configuration

**DeepEval** ([GitHub](https://github.com/confident-ai/deepeval))
- License: Apache 2.0
- Tasks: Capability assessment rubrics; automated evaluation harnesses
- Integration: Medium
- Risks: Domain-specific rubric authoring required

### API Mocking & Stubbing
**Prism (Stoplight)** ([GitHub](https://github.com/stoplightio/prism))
- License: Apache 2.0
- Tasks: Mock external APIs from OpenAPI specs; record/replay
- Integration: Low–Medium
- Risks: OpenAPI spec accuracy; simulate edge cases

**WireMock** ([GitHub](https://github.com/wiremock/wiremock))
- License: Apache 2.0
- Tasks: HTTP service virtualization for connected-mode sandboxes
- Integration: Medium
- Risks: Java dependency; consider Python alternatives like responses

---

## Implementation Priority & Quick Wins

### Start Immediately (High Priority)
1. **Milestone H**: modelcontextprotocol/python + python-jose for MCP and manifest signing
2. **Milestone J**: OPA + transitions for policy engine and simple approvals
3. **Milestone N**: testcontainers-python + Vault+hvac for sandbox MVP

### Phase 2 Sprint 1 (Weeks 1-2)
1. **Milestone M**: asyncpg + pybreaker for performance baseline
2. **Milestone K**: Celery + fastapi-limiter for billing foundation
3. **Milestone I**: TanStack Table/Query for workspace UI

### Phase 2 Sprint 2+ (Weeks 3-8)
1. **Milestone L**: Temporal + Hydra for reproducibility
2. **Milestone N**: MLflow + DeepEval for learning assessment
3. **Milestone H**: OpenTelemetry + scikit-learn for reputation

---

## Integration Examples & Code Stubs

See `docs/phase2-integration-examples.md` for FastAPI endpoint examples and minimal integration code for top-priority libraries.
