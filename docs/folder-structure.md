# Folder Structure

This guide describes the recommended monorepo layout for the PoC and early product. Adjust names to your conventions as needed.

```
collexa/
├─ frontend/                     # Next.js (TypeScript)
│  ├─ app/                       # App Router pages (e.g., /, /agents, /playground)
│  ├─ components/                # Reusable UI components
│  ├─ features/                  # Feature modules (agents, billing, auth)
│  ├─ lib/                       # API clients, utils (generated API types here)
│  ├─ hooks/                     # React hooks
│  ├─ styles/                    # Global styles
│  ├─ public/                    # Static assets
│  └─ tests/                     # Unit tests (Jest + RTL)
│
├─ backend/                      # FastAPI service (Python)
│  ├─ app/
│  │  ├─ main.py                 # FastAPI entrypoint
│  │  ├─ api/
│  │  │  ├─ routers/             # Route modules (agents.py, invoke.py, billing.py)
│  │  │  └─ deps.py              # Dependencies (auth, DB session)
│  │  ├─ schemas/                # Pydantic request/response models
│  │  ├─ services/               # Business logic (builder, adapters, learning)
│  │  ├─ repositories/           # DB access (agents, runs, keys)
│  │  ├─ models/                 # SQLAlchemy models
│  │  ├─ db/
│  │  │  ├─ session.py           # Session management
│  │  │  └─ migrations/          # Alembic migrations
│  │  ├─ security/               # JWT, API keys, RLS helpers
│  │  ├─ core/                   # Config, settings, logging
│  │  ├─ adapters/               # Protocol adapters (mcp/, a2a/, rest/)
│  │  └─ utils/                  # Helpers
│  └─ tests/                     # pytest units/integration
│
├─ docs/                         # Project docs
│  ├─ architecture.mmd           # Mermaid architecture diagram
│  ├─ poc-checklist.md           # PoC acceptance criteria
│  ├─ dev-practices.md           # Development practices
│  └─ folder-structure.md        # This file
│
├─ infra/                        # Infra as code / docker-compose for dev
│  ├─ docker-compose.yml         # DB, vector DB, object store, OTel
│  └─ terraform/                 # Cloud infra (optional later)
│
├─ scripts/                      # Dev scripts (seed, run, lint, test)
│
├─ .github/workflows/            # CI workflows
│  ├─ frontend.yml
│  └─ backend.yml
│
├─ README.md                     # Product vision and roadmap
└─ package.json / pyproject.toml # Managers at repo root (optional) 
```

## Naming and conventions
- Kebab-case for branches; snake_case for Python; camelCase for TS variables
- Keep files short; split modules when a file exceeds ~300 LOC
- One router per domain; one service layer per domain; repositories handle persistence

## Protocol adapters placement
- backend/app/adapters/mcp/: MCP server implementation and schemas
- backend/app/adapters/a2a/: A2A descriptor builder and signature logic
- backend/app/adapters/rest/: OpenAPI/REST helpers for Instructions Pack

## Where to put new things
- New UI page: frontend/app/<route>/page.tsx
- New endpoint: backend/app/api/routers/<domain>.py and schemas in backend/app/schemas/
- Background job: backend/app/services/<domain> and queue/workflow config
- Migration: backend/app/db/migrations/ via Alembic

## Tests
- frontend/tests/: Jest + RTL; mock fetch or use msw
- backend/tests/: pytest units; integration with a test DB (transactional)
- Prefer small, isolated tests; use factories/fixtures

## Environment & secrets
- frontend/.env.local and backend/.env for local dev (never commit secrets)
- Use secret manager in CI/CD; keep prod secrets out of the repo

## Linting & formatting
- Frontend: ESLint + Prettier; Backend: Ruff + Black; Types: mypy

## CI
- Separate frontend and backend workflows; cache deps; run linters and unit tests on PRs

## Notes
- Keep docs updated as structure evolves; add READMEs in subfolders for complex areas

