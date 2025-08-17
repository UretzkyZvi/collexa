#!/usr/bin/env node
/*
  Minimal MCP WS check:
  - Connect, send tools/list, then tools/call
  Usage: node scripts/mcp_check.js ws://localhost:8000/ws/mcp/agent-xyz
*/

const WebSocket = require('ws');

const url = process.argv[2] || 'ws://localhost:8000/ws/mcp/agent-xyz';
const ws = new WebSocket(url);

ws.on('open', () => {
  console.log('Connected to', url);
  ws.send(JSON.stringify({ id: 1, method: 'tools/list' }));
});

ws.on('message', (data) => {
  try {
    const msg = JSON.parse(String(data));
    console.log('Received:', msg);
    if (msg.id === 1) {
      ws.send(JSON.stringify({ id: 2, method: 'tools/call', params: { tool: 'invoke', input: { ping: 'pong' } } }));
    } else if (msg.id === 2) {
      console.log('Call result OK, closing.');
      ws.close();
    }
  } catch (e) {
    console.error('Non-JSON message:', String(data));
  }
});

ws.on('close', () => process.exit(0));
ws.on('error', (err) => {
  console.error('WS error:', err.message);
  process.exit(1);
});

