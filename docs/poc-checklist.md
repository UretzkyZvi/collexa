# PoC Checklist (Milestone-by-Milestone Acceptance Criteria)

This checklist tracks the minimum features and quality gates to accept each Phase 1 milestone.

## Milestone A — PoC UI (Next.js) + Backend (FastAPI)

- [x] Repo scaffolding: Next.js (TypeScript, App Router) + FastAPI (Python 3.11)
- [x] Env/config: .env for UI and API; secrets via .env/.env.local
- [x] CI: Lint + unit tests (UI: Jest/RTL; API: pytest) on PRs
- [x] Health endpoints: UI (/health) and API (GET /health)
- [x] CORS set for UI host (localhost:3000)
- [x] UI library: shadcn/ui initialized and core components added (Button, Input, Card, Dialog, Label, Textarea, Select, Sidebar, Breadcrumb, Separator)

Acceptance Test
- [x] Visit UI, load Describe Agent page (/agents/new), submit a sample brief; see confirmation (or use /debug/test-auth to POST /v1/agents)

- [x] Dashboard shell using shadcn/ui Sidebar (inset variant) with TeamSwitcher and UserButton
- [x] Route groups: (main) shell for post-onboarding; onboarding routes separate (no sidebar)


## Database & Schema (Postgres) — Phase 1 scope

Schema overview
- orgs: organizations/tenants (id, name, stripe_customer_id)
- users: end users (id, email, name)
- org_members: user membership and role in an org (org_id, user_id, role)
- agents: agent records (id, org_id, display_name, descriptor_json, status)
- agent_capabilities: declared capabilities per agent (agent_id, name, schema_json)
- agent_keys: per‑agent API keys (id, agent_id, key_hash, scopes, created_at, revoked_at)
- runs: invocations (id, agent_id, org_id, capability, input_json, output_json, status, started_at, finished_at, cost_tokens, cost_cents)
- logs: structured log lines for runs (id, run_id, ts, level, message, data_json)
- billing_events: metering/billing events (id, org_id, type, amount_cents, meta_json, ts)

Representative DDL (abridged)
```sql
create table orgs (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  stripe_customer_id text,
  created_at timestamptz not null default now()
);

create table users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  display_name text,
  created_at timestamptz not null default now()
);

create table org_members (
  org_id uuid not null references orgs(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null check (role in ('owner','member')),
  primary key (org_id, user_id)
);

create table agents (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references orgs(id) on delete cascade,
  display_name text not null,
  descriptor_json jsonb not null,
  status text not null default 'active',
  created_at timestamptz not null default now()
);

create table agent_keys (
  id uuid primary key default gen_random_uuid(),
  agent_id uuid not null references agents(id) on delete cascade,
  key_hash text not null,
  scopes text[] not null,
  created_at timestamptz not null default now(),
  revoked_at timestamptz
);

create table runs (
  id uuid primary key default gen_random_uuid(),
  agent_id uuid not null references agents(id) on delete cascade,
  org_id uuid not null references orgs(id) on delete cascade,
  capability text not null,
  input_json jsonb not null,
  output_json jsonb,
  status text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  cost_tokens bigint default 0,
  cost_cents integer default 0
);
```

Row‑Level Security (RLS) isolation
```sql
-- Per‑request, the API sets: set local app.org_id = '<uuid>';

alter table agents enable row level security;
create policy org_isolation_agents on agents
  using (org_id = current_setting('app.org_id', true)::uuid);

alter table runs enable row level security;
create policy org_isolation_runs on runs
  using (org_id = current_setting('app.org_id', true)::uuid);

alter table agent_keys enable row level security;
create policy org_isolation_keys on agent_keys
  using (
    exists (
      select 1 from agents a
      where a.id = agent_keys.agent_id
        and a.org_id = current_setting('app.org_id', true)::uuid
    )
  );
```

Migrations & configuration
- Use Alembic for migrations; one revision per milestone change
- FastAPI middleware: after JWT verify, set `app.org_id` for the DB session
- DB roles: separate migration role and app role; least privilege

Acceptance tests
- With `app.org_id = orgA`, selecting agents returns only orgA rows
- API calls from orgA cannot access agents/logs/runs from orgB (403 or empty)

## Milestone B — Create Agent from Brief

- [x] API: POST /v1/agents — persists to DB; returns id/endpoints (requires X-Team-Id)
- [ ] Builder stub: parse brief, select a mock capability kit, produce an Agent Descriptor
- [x] Persist agent in Postgres; return REST base URLs
- [x] UI: show agent summary and “Get Instructions Pack” CTA

- [x] Frontend: useAuthFetch attaches X-Team-Id automatically from selected team
- [x] Frontend middleware redirects unauthenticated to /handler/sign-in (public paths allowlisted)

Acceptance Test
- [x] Create an agent via POST /v1/agents, receive 200 authenticated and row exists
- [x] Retrieve its metadata via GET /v1/agents/{agent_id} with org scoping

## Milestone C — Instructions Pack

- [x] API: GET /v1/agents/{agent_id}/instructions — returns n8n/Make/LangChain/OpenAI/Claude/MCP snippets
- [x] UI: copy-to-clipboard for each snippet; placeholder host vars

Acceptance Test
- [x] Paste the n8n or Make HTTP example and receive a 200 with mock payload

## Milestone D — Invoke + Streaming Logs

- [x] API: POST /v1/agents/{agent_id}/invoke — accepts capability + input (requires X-Team-Id)
- [x] Streaming: SSE endpoints for live logs (agent-level and per-run)
- [x] UI Playground: invoke action and consume stream (PoC)
- [x] Persist run record with status and output

Acceptance Test
- [x] See logs streaming in UI and final JSON result rendered

## Milestone E — Baseline Security and Billing

- [x] AuthN: Stack Auth integrated; sign-in via /handler/sign-in; UserButton shown
- [x] Protected API with REST token verification (Stack /users/me) in FastAPI
- [x] AuthZ: team-based org_id scoping and ownership checks on GET/POST agents
- [x] Backend middleware: coarse auth on /v1/*, attaches auth context
- [x] CORS/Preflight: auth middleware bypasses OPTIONS so CORSMiddleware can reply
- [x] SSE Streams: auth middleware allows /v1/agents/{id}/logs and /v1/runs/{id}/stream (handler verifies via query token)
- [x] Debug: GET /v1/debug/me returns auth context for troubleshooting

- [x] Stricter endpoints: X-Team-Id mandatory for create/invoke; membership verified
- [x] Tenant isolation: Postgres Row-Level Security (RLS) policies + SET LOCAL app.org_id middleware + cross-org tests
- [x] API Keys: per-agent, hashed at rest, scoped to capabilities (POST/DELETE /v1/agents/{id}/keys; X-API-Key auth)
- [ ] Billing: Create Stripe customer on signup; POST /v1/billing/checkout; webhook receiver
- [ ] Audit logs: actor_id, org_id, endpoint, agent_id, capability, result status

Acceptance Test
- [x] Signed-in user can POST /v1/agents; unsigned user gets 401
- [x] User from team X cannot fetch agent from team Y (404)

## Frontend Integration and UX

- [x] useAuthFetch hook attaches Authorization and X-Team-Id
- [x] Onboarding: create team and select team flows (non-skippable)
- [x] Jest tests: auth fetch helper, onboarding components, Playground invoke/stream, useAuthFetch X-Team-Id behavior
- [x] UI library: shadcn/ui initialized (Button, Input, Card, Dialog, Label, Textarea, Select, Sidebar, Breadcrumb, Separator)
- [x] Next middleware: redirect unauthenticated users (public paths allowlisted)
- [x] Dashboard layout with Sidebar (inset), TeamSwitcher, UserButton

Acceptance Test
- [x] After signup without teams, user is redirected to onboarding; creating a team selects it and redirects to main app
- [x] API calls after onboarding include X-Team-Id implicitly


## Milestone F — A2A Descriptor + MCP Adapter (Basic)

- [x] API: /.well-known/a2a/{agent_id}.json — signed capability descriptor (HS256)
- [x] MCP: Basic tool advertisement for the agent via WebSocket (list + echo)
- [x] Quick demo: external MCP client lists tools successfully (see docs/mcp-validation.md)

Acceptance Test

## Current Sprint (PoC acceptance — 1–2 weeks)

Instructions Pack
- [x] API: GET /v1/agents/{agent_id}/instructions returns concrete snippets (n8n/Make/LangChain/OpenAI/Claude/MCP) — DONE
- [x] UI: Instructions page with copy-to-clipboard and <host>/<agent-id> variableization — DONE (PR #23)

Streaming Logs + Persistence
- [x] Backend: SSE endpoints (agent-level and per-run) for live logs during invoke
- [x] Frontend: Playground subscribes via EventSource and renders progressive logs
- [x] Persistence: create Run on start; append Log events; finalize status + output

Logs UI
- [x] Endpoints: GET /v1/runs and GET /v1/runs/{id}/logs
- [x] Minimal Logs page with Live toggle; filters (agent/status)

Security & Platform
- [x] Postgres RLS policies in place + middleware to SET LOCAL app.org_id; enforcement tests
- [x] CI on PRs: frontend (lint, typecheck, Jest), backend (ruff, black --check, mypy, pytest)
- [x] FastAPI tests: CORS OPTIONS bypass, SSE path bypass, /v1/debug/me auth context

Optional (in parallel): Protocols
- [ ] /.well-known/a2a/{agent_id}.json — signed (static initial)
- [ ] Minimal MCP server advertising 1–2 mock tools; verify client can list tools

## Backlog (Shortlist)

- [ ] Basic Settings page scaffold
- [x] API Keys: create/list/revoke; hashed storage — DONE (feat/api-keys branch)
- [ ] Stripe integration: customer on signup + checkout flow + webhook
- [ ] Observability: request_id + basic metrics
- [ ] An MCP client connects and sees the advertised tools; A2A descriptor validates

## Milestone G — Observability (Minimal)

- [ ] Structured logs with request_id, org_id, agent_id
- [ ] Basic metrics (invocations count, latency p50/p95, errors)
- [ ] Tracing stub (OpenTelemetry collector optional)

Acceptance Test
- [ ] Dashboard or log view shows recent invocations with status/latency

Notes
- Keep Phase 1 minimal but production-safe. Defer enterprise features (SSO, OPA policies) to Phase 2.

