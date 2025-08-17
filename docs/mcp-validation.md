# Manual MCP Validation Guide

This guide shows how to validate the basic MCP (Model Context Protocol) WebSocket server implemented in this PoC and verify that an external client can list and call tools.

## Prerequisites
- Backend running locally (FastAPI dev server):
  - `uvicorn app.main:app --reload --port 8000`
- Node 18+ (only if you want to run the optional CLI script)

## Endpoints
- MCP WebSocket: `ws://localhost:8000/ws/mcp/<agent_id>`
- A2A Descriptor: `http://localhost:8000/v1/.well-known/a2a/<agent_id>.json`

The MCP server supports:
- `tools/list` → returns an array of tool definitions
- `tools/call` → echoes the input

## Quick test using `wscat` (or any WS client)
1. Install wscat (optional): `npm i -g wscat`
2. Connect:
   - `wscat -c ws://localhost:8000/ws/mcp/agent-xyz`
3. List tools:
```
{"id":1, "method":"tools/list"}
```
4. Call a tool (echo):
```
{"id":2, "method":"tools/call", "params": {"tool": "invoke", "input": {"hello": "world"}}}
```
You should see a JSON response reflecting the called tool, the agent_id, and the echoed input.

## Optional: Node CLI script
Use the provided script to perform the handshake and simple calls programmatically.

- Run: `node scripts/mcp_check.js ws://localhost:8000/ws/mcp/agent-xyz`
- Expected output:
  - A tools list array
  - A result object from `tools/call` with the echoed payload

## Using a GUI client (e.g., Thunder Client)
1. Create a new WebSocket request: `ws://localhost:8000/ws/mcp/agent-xyz`
2. Send `{ "id": 1, "method": "tools/list" }`
3. Send `{ "id": 2, "method": "tools/call", "params": { "tool": "invoke", "input": { "x": 1 } } }`

## A2A Descriptor (for reference)
- Fetch `http://localhost:8000/v1/.well-known/a2a/agent-xyz.json`
- The response includes signed endpoints and capability list.

## Troubleshooting
- 404 on WS: ensure backend is running and the path is `/ws/mcp/<agent_id>`
- Connection closes: check backend logs for exceptions
- Firewalls/proxies: ensure WS connections to localhost:8000 are allowed

## Acceptance for Milestone F
- External client can successfully list tools and call a tool via WS
- A2A descriptor can be fetched for a sample agent

After you complete this validation, mark the Milestone F acceptance as done in `docs/poc-checklist.md`.

