# Quick Start Guide

Get up and running with Collexa in under 5 minutes! This guide will help you create your first AI agent and make your first API call.

## Prerequisites

- Node.js 18+ and npm/pnpm
- Python 3.11+
- PostgreSQL 14+ (or use Docker)
- Git

## 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/UretzkyZvi/collexa.git
cd collexa

# Start with Docker (recommended)
docker-compose up -d

# Or run locally (see Installation guide for details)
```

## 2. Access the Dashboard

1. Open your browser to `http://localhost:3000`
2. Sign up for a new account
3. Create your first organization when prompted

![Dashboard Screenshot](../assets/dashboard-welcome.png)

## 3. Create Your First Agent

1. Click **"Create Agent"** from the dashboard
2. Enter a brief description:
   ```
   A helpful assistant that can answer questions about programming and provide code examples.
   ```
3. Click **"Create Agent"**
4. Your agent is now ready! 🎉

![Agent Creation](../assets/agent-creation.png)

## 4. Test Your Agent

### Via Dashboard (Playground)

1. Go to **Playground** in the sidebar
2. Select your agent
3. Enter a test message:
   ```json
   {
     "capability": "help",
     "input": {
       "question": "How do I create a REST API in Python?"
     }
   }
   ```
4. Click **"Invoke"** and watch the real-time logs!

### Via API

1. Go to **Settings** → **API Keys**
2. Create a new API key for your agent
3. Copy the key (save it - you won't see it again!)
4. Test with curl:

```bash
curl -X POST http://localhost:8000/v1/agents/{AGENT_ID}/invoke \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "help",
    "input": {
      "question": "Hello, world!"
    }
  }'
```

## 5. Monitor Performance

1. Return to the **Dashboard**
2. View real-time metrics:
   - API call count and success rate
   - Response latency (p50, p95, p99)
   - Agent invocation statistics

![Metrics Dashboard](../assets/metrics-dashboard.png)

## 6. Integration Ready!

Your agent is now ready for integration with:

- **n8n**: Use HTTP Request nodes with your API key
- **Make.com**: Create scenarios with HTTP modules
- **LangChain**: Use our Python SDK
- **Custom Apps**: REST API with any language

Get integration snippets from your agent's **Instructions** page!

## Next Steps

🎯 **You're all set!** Here's what to explore next:

- **[First Agent Tutorial](./first-agent.md)** - Detailed agent creation guide
- **[Core Concepts](./concepts.md)** - Understand the platform fundamentals
- **[n8n Integration](../integrations/n8n.md)** - Connect with n8n workflows
- **[API Reference](../api/overview.md)** - Complete API documentation

## Troubleshooting

### Common Issues

**Agent creation fails**
- Ensure you're logged in and have selected an organization
- Check browser console for errors

**API calls return 401**
- Verify your API key is correct
- Ensure the key belongs to the correct agent and organization

**Dashboard shows no metrics**
- Make at least one API call to see metrics
- Metrics update in real-time after the first invocation

**Need Help?**
- Check the [User Guide](../user-guide/dashboard.md)
- Review [API Documentation](../api/overview.md)
- Open an issue on [GitHub](https://github.com/UretzkyZvi/collexa/issues)

---

**Next**: [Installation Guide →](./installation.md)
