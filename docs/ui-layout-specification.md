# UI / UX Specification

This document describes the target UI/UX for the PoC. It covers the authentication surfaces, onboarding, dashboard, agent management, playground, logs, settings, navigation, and responsive considerations. Each section includes a wireframe description, component breakdown, and integration points with Stack Auth and the FastAPI backend.

## Global Principles
- Use Next.js App Router and client/server components appropriately
- Stack Auth provides session, user, teams, and team selection; use `useUser`, `UserButton`, handler routes
- Use `useAuthFetch` to automatically set `Authorization: Bearer` and `X-Team-Id` headers
- shadcn/ui for core components: Button, Input, Card, Dialog, Label, Textarea, Select
- Tailwind for layout and styling; consistent spacing scale and typography

---

## Authentication Pages

### Sign-in and Sign-up
Wireframe (textual):
- Centered Card with product logo/title
- Tabs: Sign in | Sign up (Stack handler pages)
- Primary button to continue
- Footer: "By continuing you agree to..."

Components:
- Card: container
- UserButton (after auth) in app chrome
- Stack routes: `/handler/sign-in`, `/handler/sign-up`

Integration:
- Uses Stack Auth handlers; no custom forms
- After auth, app shell loads and `OnboardingGate` checks team state

---

## Onboarding Flow

### Create Team page `/onboarding`
Wireframe:
- Card
  - Heading: "Create your team"
  - Input: Team name (required)
  - Textarea: Description (optional)
  - Button: Create Team (loading state)
  - Error banner on failure

Components:
- Input, Textarea, Button, Label, Card

Integration:
- `user.createTeam({ displayName })`
- If description provided: `team.update({ clientMetadata: { description } })`
- `user.setSelectedTeam(team)`
- Redirect to `/`

### Select Team page `/onboarding/select-team`
Wireframe:
- List of teams as buttons within a Card
- Each item: displayName + small id caption

Components:
- Card, Button, List/Stack

Integration:
- `user.useTeams()` to get teams
- `user.setSelectedTeam(team)` and redirect to `/`

Gate Enforcement:
- `OnboardingGate` redirects to `/onboarding` if `useTeams().length === 0`
- Redirects to `/onboarding/select-team` if teams exist but `selectedTeam` is unset

---

## Main Dashboard (Post-onboarding)

Wireframe:
- Header (top) with:
  - Logo/name (left)
  - Team switcher (center or left)
  - UserButton (right)
- Sidebar (optional, desktop) with navigation
- Main content: routes render area

Components:
- Header: logo, team switcher (Select), nav links
- Team switcher reads `user.useTeams()` and calls `user.setSelectedTeam()`
- Button, Card, Nav link components

Integration:
- `useAuthFetch` ensures API calls carry `X-Team-Id`
- For SSR pages calling the API from server, optionally store selected team in cookie and forward header

---

## Agent Management

### Agent creation `/agents/new`
Wireframe:
- Card
  - Textarea for brief
  - Button: Create Agent
  - Result area with JSON

Components:
- Textarea, Button, Card

Integration:
- POST `/v1/agents` with body `{ brief }` via `useAuthFetch`
- Response includes `agent_id`, `org_id`, `created_by`

### Agent list `/agents`
Wireframe:
- Cards for each agent with name and quick actions

Components:
- Card grid, Button(s)

Integration:
- GET `/v1/agents` (future) scoped by team/org_id

### Agent details `/agents/[id]`
Wireframe:
- Card with title, metadata, and action buttons (Invoke, Instructions)

Components:
- Card, Button

Integration:
- GET `/v1/agents/{id}` (implemented)

### Instructions `/agents/[id]/instructions`
Wireframe:
- Card with code blocks for each integration (n8n, Make, LangChain, OpenAI, Claude, MCP)

Components:
- Card, pre/code blocks, Button for copy

Integration:
- GET `/v1/agents/{id}/instructions` (stub)

---

## Playground `/playground`
Wireframe:
- Card
  - Inputs: Agent ID, Capability, JSON input
  - Button: Invoke
  - Log area (stream)

Components:
- Input, Textarea, Button, Card

Integration:
- POST `/v1/agents/{id}/invoke` (stub)
- SSE/WebSocket logs endpoint (future)

---

## Logs `/logs`
Wireframe:
- Card with table/list of recent runs
- Filters for agent/capability

Components:
- Table, Select, Input, Card

Integration:
- GET `/v1/runs` (future)
- GET `/v1/runs/{id}/logs` (future)

---

## Settings `/settings`
Wireframe:
- Card sections: Profile, Team, Billing (future)

Components:
- Card, Input, Button, Dialog for destructive actions

Integration:
- Profile updates via Stack client
- Team updates via Stack team API
- Billing via Stripe (future)

---

## Navigation Structure

- Header with brand, team switcher, nav links, UserButton
- Sidebar (desktop) with key sections (Dashboard, Agents, Playground, Logs, Settings)
- Breadcrumbs in content area (optional)
- Route groups in Next app directory: (main) for app shell, onboarding routes separate

---

## Responsive Design

- Mobile: single-column, header transforms into menu with Drawer/Dialog for nav
- Desktop: sidebar visible, content in 8–12 column grid
- Buttons and inputs sized appropriately for touch on mobile

---

## Reusable Components & Variants

- Button: variant (primary, secondary, ghost), size (sm, md, lg)
- Input/Textarea: with label and error message props
- Card: header, content, footer slots
- Dialog: title, description, footer actions
- Select: items, onChange, selected value
- TeamSwitcher: reads teams and updates selected team
- Form components should expose error and loading states

Props examples:
- `<Button variant="primary" size="md" isLoading>`
- `<Input label="Team name" error="Required" />`
- `<Dialog open={open} onOpenChange={setOpen} />`

---

## Integration Points Summary

- Auth: Stack handlers and `useUser`, redirect gating with `OnboardingGate`
- Team context: `selectedTeam` and `X-Team-Id` header via `useAuthFetch`
- Backend: FastAPI endpoints (`/v1/agents`, `/v1/agents/{id}`, ...)
- DB: org_id scoping enforced in app and ready for RLS

---

## Open Questions / Future Work
- Server-side selected team cookie for SSR API calls
- Full RLS policies and SET LOCAL helper middleware
- Agent list and runs/logs UIs
- Toast system for success/error feedback (shadcn/ui `use-toast`)
- Theme and brand customization

