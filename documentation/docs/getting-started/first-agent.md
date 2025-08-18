# Your First Agent

This tutorial walks you through creating, configuring, and testing your first AI agent in detail. By the end, you'll understand how agents work and how to integrate them with external tools.

## What You'll Learn

- How to create and configure agents
- Understanding agent capabilities and inputs
- Testing agents through the UI and API
- Monitoring agent performance
- Getting integration code for external tools

## Step 1: Create an Agent

### Via Dashboard

1. **Navigate to Agents**
   - Click **"Agents"** in the sidebar
   - Click **"Create New Agent"** button

2. **Enter Agent Details**
   ```
   Brief: A customer support assistant that can help with product questions, 
   troubleshooting, and order inquiries. It should be friendly, helpful, 
   and provide clear step-by-step solutions.
   ```

3. **Review Generated Configuration**
   - The system creates an agent with a unique ID
   - Default capabilities are configured
   - Agent is immediately available for use

### Via API

```bash
curl -X POST http://localhost:8000/v1/agents \
  -H "Authorization: Bearer your-token" \
  -H "X-Team-Id: your-org-id" \
  -H "Content-Type: application/json" \
  -d '{
    "brief": "A customer support assistant that can help with product questions, troubleshooting, and order inquiries."
  }'
```

**Response:**
```json
{
  "agent_id": "agent_abc123",
  "display_name": "Customer Support Assistant",
  "brief": "A customer support assistant...",
  "created_at": "2025-01-18T10:00:00Z",
  "endpoints": {
    "invoke": "/v1/agents/agent_abc123/invoke",
    "logs": "/v1/agents/agent_abc123/logs",
    "instructions": "/v1/agents/agent_abc123/instructions"
  }
}
```

## Step 2: Understanding Your Agent

### Agent Properties

- **Agent ID**: Unique identifier (`agent_abc123`)
- **Display Name**: Human-readable name
- **Brief**: Description of the agent's purpose
- **Capabilities**: What the agent can do
- **Endpoints**: API URLs for interaction

### Default Capabilities

Every agent starts with these capabilities:
- **help**: General assistance and information
- **echo**: Simple input/output testing
- **status**: Agent health and information

## Step 3: Test Your Agent

### Using the Playground

1. **Navigate to Playground**
   - Click **"Playground"** in the sidebar
   - Select your agent from the dropdown

2. **Basic Test**
   ```json
   {
     "capability": "help",
     "input": {
       "question": "How do I reset my password?"
     }
   }
   ```

3. **Watch Real-time Logs**
   - See the agent processing your request
   - View structured log output
   - Monitor execution time and status

### Using the API

```bash
curl -X POST http://localhost:8000/v1/agents/agent_abc123/invoke \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "help",
    "input": {
      "question": "How do I reset my password?",
      "context": {
        "user_type": "premium",
        "product": "web_app"
      }
    }
  }'
```

**Response:**
```json
{
  "agent_id": "agent_abc123",
  "status": "succeeded",
  "run_id": "run_xyz789",
  "result": {
    "echo": {
      "capability": "help",
      "input": {
        "question": "How do I reset my password?",
        "context": {
          "user_type": "premium",
          "product": "web_app"
        }
      }
    }
  }
}
```

## Step 4: Monitor Performance

### Dashboard Metrics

1. **Go to Dashboard**
   - View agent invocation count
   - See success rate and error metrics
   - Monitor response latency

2. **Performance Breakdown**
   - **P50 Latency**: Median response time
   - **P95 Latency**: 95th percentile response time
   - **Success Rate**: Percentage of successful invocations

### Execution Logs

1. **Navigate to Logs**
   - Click **"Logs"** in the sidebar
   - Filter by agent, status, or time range

2. **Log Details**
   - Request/response data
   - Execution timeline
   - Error messages and stack traces

## Step 5: Get Integration Code

### Instructions Pack

1. **Navigate to Agent Instructions**
   - Go to **Agents** → Select your agent → **Instructions**
   - Or visit `/agents/{agent_id}/instructions`

2. **Copy Integration Snippets**

**n8n HTTP Request Node:**
```json
{
  "method": "POST",
  "url": "http://localhost:8000/v1/agents/agent_abc123/invoke",
  "headers": {
    "X-API-Key": "your-api-key",
    "Content-Type": "application/json"
  },
  "body": {
    "capability": "help",
    "input": {
      "question": "{{$json.question}}"
    }
  }
}
```

**Make.com HTTP Module:**
```json
{
  "url": "http://localhost:8000/v1/agents/agent_abc123/invoke",
  "method": "POST",
  "headers": [
    {
      "name": "X-API-Key",
      "value": "your-api-key"
    }
  ],
  "body": {
    "capability": "help",
    "input": {
      "question": "{{question}}"
    }
  }
}
```

**Python (LangChain):**
```python
import requests

def invoke_agent(question):
    response = requests.post(
        "http://localhost:8000/v1/agents/agent_abc123/invoke",
        headers={
            "X-API-Key": "your-api-key",
            "Content-Type": "application/json"
        },
        json={
            "capability": "help",
            "input": {"question": question}
        }
    )
    return response.json()

result = invoke_agent("How do I reset my password?")
print(result)
```

## Step 6: Advanced Testing

### Different Capabilities

Test various capabilities your agent supports:

```bash
# Help capability
curl -X POST .../invoke -d '{"capability": "help", "input": {"question": "..."}}'

# Echo capability (for testing)
curl -X POST .../invoke -d '{"capability": "echo", "input": {"test": "data"}}'

# Status capability
curl -X POST .../invoke -d '{"capability": "status", "input": {}}'
```

### Error Handling

Test error scenarios:

```bash
# Invalid capability
curl -X POST .../invoke -d '{"capability": "invalid", "input": {}}'

# Missing input
curl -X POST .../invoke -d '{"capability": "help"}'

# Invalid API key
curl -X POST .../invoke -H "X-API-Key: invalid" -d '{"capability": "help", "input": {}}'
```

## Next Steps

🎉 **Congratulations!** You've successfully created and tested your first agent.

### What's Next?

1. **[Core Concepts](./concepts.md)** - Understand platform fundamentals
2. **[User Guide](../user-guide/dashboard.md)** - Explore all platform features
3. **[n8n Integration](../integrations/n8n.md)** - Connect with automation workflows
4. **[API Reference](../api/overview.md)** - Complete API documentation

### Advanced Topics

- **Custom Capabilities**: Extend your agent with new functions
- **Webhook Integration**: Receive real-time notifications
- **Batch Processing**: Handle multiple requests efficiently
- **Performance Optimization**: Scale for production workloads

---

**Next**: [Core Concepts →](./concepts.md)
