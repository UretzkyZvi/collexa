# Phase 2 Checklist (Milestone-by-Milestone Acceptance Criteria)

## 🚀 Phase 2 Status: IN PROGRESS

Phase 2 focuses on interoperability, security hardening, billing, and reproducibility. It builds directly on the completed Phase 1 PoC and moves the platform toward enterprise readiness and cross-agent collaboration.

- Target Window: Months 3–4
- KPIs: cross‑agent invocation p50 < 2s; reproducible runs with signed logs
- Carryovers from Phase 1: Stripe integration; builder stub (optional)

### � Supporting Documentation
- **[Phase 2 Dependencies](./phase2-dependencies.md)**: Open-source library recommendations with licenses, integration complexity, and risks
- **[Phase 2 Integration Examples](./phase2-integration-examples.md)**: FastAPI code stubs and minimal integration examples for priority libraries

### �📌 Planned Milestones
- Milestone H: Interoperability Core (MCP/A2A + Tool Sharing + Manifests + Reputation)
- Milestone I: Workspace UI & Organization Settings
- Milestone J: Advanced Security (RBAC/ABAC via OPA, SSO)
- Milestone N: Agent Sandbox Environments & Autonomous Learning
- Milestone K: Billing & Budgets (Stripe Integration)
- Milestone L: Reproducibility & Signed Logs
- Milestone M: Performance & Reliability (p50 < 2s)

---

This checklist tracks the minimum features and quality gates to accept each Phase 2 milestone.

## Database & Schema (Postgres) — Phase 2 scope

Schema extensions (new or updated)
- orgs: ensure stripe_customer_id is populated via Stripe (Milestone K)
- org_policies: OPA policy references per org (id, org_id, name, rego_text, version, created_at)
- roles, permissions, role_permissions: RBAC (role, permission) mapping (Milestone J)
- approvals: approval gates for sensitive ops (id, org_id, subject_type, subject_id, status, approver_id, created_at, decided_at)
- budgets: per org/agent budgets (org_id, agent_id, period, limit_cents, alerts_json)
- a2a_manifests: signed capability manifests (id, agent_id, version, manifest_json, signature, key_id, created_at)
- provenance: signed run provenance (run_id, manifest_id, signature, verifier, created_at)
- reputation: agent reputation summaries (agent_id, score, signals_json, updated_at)
- sandboxes: sandbox instances (id, agent_id, org_id, mode: mock|emulated|connected, target_system, config_json, status, created_at)
- sandbox_runs: learning/eval attempts within a sandbox (id, sandbox_id, phase: learn|eval, task_name, status, input_json, output_json, error_json, started_at, finished_at)
- learning_plans: curriculum and objectives (id, agent_id, target_system, objectives_json, curriculum_json, status)
- capability_assessments: rubric-based competency records (id, agent_id, target_system, rubric_json, score, last_evaluated_at, evidence_run_ids)
- credentials: secret_ref to external vault and scopes metadata (id, org_id, agent_id, target_system, secret_ref, scopes, created_at)

Migrations & configuration
- Use Alembic migrations; 1+ revisions per milestone touching schema
- Maintain least-privilege DB roles; extend RLS policies to new tables

Acceptance tests
- With app.org_id set, all CRUD on new tables are tenant-isolated via RLS
- Foreign keys and cascading deletes behave as expected for agents/runs/manifests

## Milestone H — Interoperability Core (MCP/A2A + Tool Sharing + Manifests + Reputation)

Dependencies
- Phase 1: Basic MCP server, signed A2A descriptor present

**Key Libraries** (see [phase2-dependencies.md](./phase2-dependencies.md#milestone-h--interoperability-core))
- modelcontextprotocol/python (MIT) - MCP server/client primitives
- python-jose (MIT) - Manifest signing and A2A descriptor verification
- OpenTelemetry (Apache 2.0) - Cross-agent metrics for reputation
- scikit-learn + river (BSD/MIT) - Reputation scoring algorithms

Tasks
- [ ] MCP: advertise real tool schemas with auth requirements; support capability invocation proxying
- [ ] A2A: rotate and validate signed capability descriptors (key rotation + kid)
- [ ] Cross‑agent tool sharing: allow Agent A to invoke Agent B via A2A with proper scoping and budgets
- [x] **H.1 COMPLETE**: Manifest signing: produce versioned capability manifests; store signature + key_id ✅
- [ ] Basic reputation: maintain per‑agent reliability and latency signals; compute a score
- [ ] Policy hooks: pre‑invoke check (OPA) for cross‑agent calls

Acceptance Tests
- [ ] External MCP client lists tools with schemas; invocation succeeds with auth
- [ ] A2A descriptor signature validates; key rotation maintains validity for new descriptors
- [ ] Agent A invokes Agent B; run recorded in both agents’ logs with linked provenance
- [x] **H.1 COMPLETE**: Manifest signature verifies using published key; mismatch is rejected ✅
- [ ] Reputation score updates after N runs; visible via GET /v1/agents/{id}

## Milestone I — Workspace UI & Organization Settings

Dependencies
- Phase 1: AuthN/AuthZ base, Dashboard shell, Logs UI

**Key Libraries** (see [phase2-dependencies.md](./phase2-dependencies.md#milestone-i--workspace-ui--organization-settings))
- TanStack Table + Query (MIT) - Advanced filtering/sorting, server-driven queries
- Recharts (MIT) - Budget/usage charts and metrics visualization
- react-hook-form + zod (MIT) - Form validation and budget configuration
- Apprise (BSD-2-Clause) - Multi-channel alerts for budget events

Tasks
- [ ] Projects/workspaces: create/select project; group agents, runs, logs by project
- [ ] Agent management: create/edit; manage capabilities and keys; view reputation and manifests
- [ ] Budgets UI: set org/agent budget limits; alerts configuration
- [ ] Logs & runs: improved filters (project/agent/status), replay link to reproduce run
- [ ] Org Settings: domain, SSO providers (placeholders), policy attachments (view‑only pending Milestone J)
- [ ] UX polish: empty states, error handling, accessibility checks

Acceptance Tests
- [ ] Users can create a project and scope views to it; all calls include project context
- [ ] Budgets visible and editable; over‑budget banner appears and prevents invoke if configured
- [ ] Runs list supports filter by project/agent/status/date; deep link to run details works

## Milestone J — Advanced Security (RBAC/ABAC via OPA, SSO, Approvals)

Dependencies
- Milestone I (Org Settings surfaces), DB schema for policies/roles/approvals

**Key Libraries** (see [phase2-dependencies.md](./phase2-dependencies.md#milestone-j--advanced-security))
- Open Policy Agent (Apache 2.0) - ABAC policy engine and evaluation
- Authlib (BSD) - OIDC/OAuth2 providers and token verification
- python3-saml (MIT) - SAML SSO integration
- transitions (MIT) - Lightweight approval state flows
- structlog (MIT) - Structured audit logging

Tasks
- [ ] RBAC: define roles (owner, admin, member, viewer) and permissions; enforce at API layer
- [x] **J.1 COMPLETE**: ABAC via OPA: authoring and evaluation for data/tool access; attach policy bundle per org ✅
- [ ] SSO (SAML/OIDC): integrate one provider end‑to‑end; map SSO groups to roles
- [ ] Approvals: policy‑gated approvals for sensitive actions (external network calls, budget overrides)
- [ ] Audit expansion: record policy decisions and approval trails

Acceptance Tests
- [ ] Permissions matrix enforced (unit/integration); unauthorized actions return 403/404
- [x] **J.1 COMPLETE**: OPA policies can deny an invoke based on attributes (user role, project tag); decision logged ✅
- [ ] SSO login completes; role mapped from group claim; local user/session created
- [ ] Approval required path blocks until approved; approval and execution are fully logged


## Milestone N — Agent Sandbox Environments & Autonomous Learning

Dependencies
- Milestone H (manifests/tool schemas for capability exposure)
- Milestone J (security controls, approvals, credentials handling)

**Key Libraries** (see [phase2-dependencies.md](./phase2-dependencies.md#milestone-n--agent-sandbox-environments))
- testcontainers-python (MIT) - Ephemeral sandbox containers for learning runs
- HashiCorp Vault + hvac (MPL 2.0/Apache 2.0) - Secure credential storage/rotation
- DSPy (Apache 2.0) - Autonomous learning loops and prompt optimization
- MLflow (Apache 2.0) - Learning progress tracking and metrics
- DeepEval (Apache 2.0) - Capability assessment rubrics and evaluation
- Prism (Apache 2.0) - Mock external APIs from OpenAPI specs

Tasks
- [x] **N.1 COMPLETE**: Sandbox isolation: dynamic mock mode with on-demand containers and template-based customization ✅
- [x] **N.1 COMPLETE**: Provisioning API: POST /v1/agents/{id}/sandboxes — create with required_services, custom_configs, TTL; full CRUD lifecycle ✅
- [ ] Credential management: integrate secret vault (secret_ref); enforce scoped access and rotation; attach to sandbox via policy
- [ ] Learning plan: derive curriculum from docs/specs and common tasks; persist objectives and sequence
- [ ] Autonomous learning loop: read docs/specs, attempt tasks, analyze errors, refine prompts/tools, retry until proficiency thresholds
- [ ] Safety guardrails: rate limits, data masking, read/write constraints; approvals required for connected mode writes
- [ ] Progress tracking: record sandbox_runs with outcomes; compute learning metrics (success rate, retries, time-to-proficiency)
- [ ] Capability assessment: rubric-based evaluation; update agent capabilities with proficiency flags
- [x] **N.1 COMPLETE**: UI: Sandbox tab per agent showing services, status, TTL, proxy access ✅

Acceptance Tests
- [x] **N.1 COMPLETE**: Dynamic sandbox creation with multi-service support and custom configurations ✅
- [x] **N.1 COMPLETE**: Mock mode with template-based API responses and per-agent customization ✅
- [x] **N.1 COMPLETE**: Full CRUD API with proper authentication, validation, and error handling ✅
- [x] **N.1 COMPLETE**: Frontend integration showing sandbox services, status, and proxy access ✅
- [x] **N.1 COMPLETE**: Comprehensive test suite (9/9 tests passing) with proper mocking ✅
- [ ] Creating a sandbox with connected mode requires scoped credentials and policy approval; audit log recorded
- [ ] In mock/emulated mode, agent completes a predefined curriculum without external side effects
- [ ] Learning loop improves success rate over attempts and reaches proficiency threshold for target tasks
- [ ] Capability assessment stored and visible via GET /v1/agents/{id}; UI shows competency badge
- [ ] Resetting a sandbox clears state but preserves provenance logs and assessments

## Milestone K — Billing & Budgets (Stripe Integration)

Dependencies
- Phase 1 backlog item; Milestone I (Budgets UI)

**Key Libraries** (see [phase2-dependencies.md](./phase2-dependencies.md#milestone-k--billing--budgets))
- Celery (BSD) - Async processing of Stripe webhooks and metering
- fastapi-limiter (MIT) - Budget enforcement via rate/quotas per org/agent
- APScheduler (MIT) - Scheduled budget checks and threshold alerts
- OpenMeter (Apache 2.0) - Usage metering pipeline and aggregation

Tasks
- [ ] Stripe customer creation on signup; store stripe_customer_id in orgs
- [ ] Checkout flow for paid plans; webhooks for subscription lifecycle (created/updated/canceled)
- [ ] Metering webhook(s): post usage from runs to Stripe (or internal ledger) with cost tokens/cents
- [ ] Budget enforcement: soft/hard caps at org/agent level; alerts via email/webhook
- [ ] Admin UI: plan status, payment method, invoices

Acceptance Tests
- [ ] New org triggers Stripe customer; ID stored; webhook verifies signature
- [ ] Successful checkout updates plan in DB; cancel/delinquent reflected within 5 min
- [ ] Over‑budget invoke returns 402/429 as configured; alert sent and logged

## Milestone L — Reproducibility & Signed Logs

Dependencies
- Milestone H (manifests), Phase 1 Observability base

**Key Libraries** (see [phase2-dependencies.md](./phase2-dependencies.md#milestone-l--reproducibility--signed-logs))
- Temporal (MIT) - Deterministic workflows and replay capabilities
- Hydra (MIT) - Deterministic run config management
- DeepDiff (MIT) - Structured diff for replay output comparisons
- python-prov (BSD) - Provenance model for run artifacts and lineage

Tasks
- [ ] Deterministic run config: persist model, parameters, tool versions, prompts, environment vars (non‑secret)
- [ ] Signed run provenance: link run → manifest → signature; publish verifier info
- [ ] Replay endpoint: POST /v1/runs/{id}/replay reproduces result where deterministic; flags drift
- [ ] Export bundle: downloadable package with manifest, prompts, logs excerpt, metrics

Acceptance Tests
- [ ] A recorded run can be verified (signature, manifest) and replayed; outputs match within tolerance
- [ ] Drift surfaced when tools/models changed; UI badge indicates unreproducible

## Milestone M — Performance & Reliability (p50 < 2s cross‑agent)

Dependencies
- Milestone H (cross‑agent), baseline metrics in Phase 1

**Key Libraries** (see [phase2-dependencies.md](./phase2-dependencies.md#milestone-m--performance--reliability))
- Locust (MIT) - Load testing single- and cross-agent paths
- asyncpg (BSD-3-Clause) - High-performance Postgres with pooling
- httpx (BSD-3-Clause) - Efficient upstream calls with connection pooling
- fastapi-cache2 (MIT) - Caching hot descriptors/manifests
- pybreaker (MIT) - Circuit breakers and fallbacks for dependent agents

Tasks
- [ ] Performance baselines: load tests for single‑agent and cross‑agent paths
- [ ] Latency work: connection pooling, async I/O, caching hot descriptors, streaming optimizations

- [ ] N.1 Sandbox scaffold: mock mode + learning plan + progress tracking skeleton


- [ ] Reliability: retries with idempotency keys; circuit breakers for dependent agents/tools
- [ ] SLOs: define p50/p95 targets and error budgets; alerting rules

Acceptance Tests
- [ ] Load test report shows cross‑agent invoke p50 < 2s, p95 within agreed budget
- [ ] Error budget policy created; alert triggers on breach; dashboard shows trends

## Frontend Integration and UX — Phase 2 Enhancements

**Integration Examples**: See [phase2-integration-examples.md](./phase2-integration-examples.md) for FastAPI endpoint examples and minimal integration code for priority libraries.

Tasks
- [ ] Extend Jest tests: projects/workspaces, budgets UI, replay flow, policy‑gated UI
- [ ] E2E smoke: basic flows (create project, add agent, set budget, invoke, replay)
- [ ] Accessibility and responsiveness audits across new pages

Acceptance Tests
- [ ] Jest suites pass in CI; coverage maintained or improved
- [ ] E2E smoke passes in CI on PRs; failures block merge

## Current Sprint (Phase 2 kickoff — 1–2 weeks)

- [ ] K.1 Stripe: customer + checkout + webhooks (happy path)
- [ ] I.1 Budgets UI scaffold and persistence (org/agent)
- [x] **J.1 COMPLETE**: OPA scaffold: policy bundle model + evaluation stub integrated ✅
- [x] **H.1 COMPLETE**: Manifest signing prototype and key rotation plan ✅

## Next Sprint (Phase 2 continuation)

- [x] **N.1 COMPLETE**: Agent Sandbox Environments - dynamic mock mode with template-based customization ✅
- [ ] **N.2 NEXT**: Learning plan + autonomous learning loop + progress tracking
- [ ] I.1 Budgets UI scaffold and persistence (org/agent)
- [ ] K.1 Stripe: customer + checkout + webhooks (happy path)

## Backlog (Shortlist)

- [ ] Agent Builder v1: parse brief → blueprint (role, capabilities) with mock kit selection
- [ ] Additional SSO providers (Azure AD, Okta) beyond initial
- [ ] Reputation signals: peer endorsements and anomaly detection
- [ ] Matrix/WebRTC exploration for real‑time collaboration

## Notes

- Keep Phase 2 focused on interoperability, governance, and commercial readiness.
- Defer broad observability dashboards and SDKs to Phase 3/4 unless required by KPIs.

