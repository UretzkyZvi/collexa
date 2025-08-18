# API Key Management

API keys provide secure access to your agents from external tools and applications. Learn how to create, manage, and use them effectively.

## Understanding API Keys

### What are API Keys?

API keys are secure tokens that allow external applications to:
- Invoke your agents without user authentication
- Access specific agents within your organization
- Integrate with tools like n8n, Make.com, and custom applications
- Maintain security through scoped access

### Key Features

- **Agent-Scoped**: Each key is tied to a specific agent and organization
- **Secure Storage**: Keys are hashed using SHA-256 and never stored in plain text
- **Revocable**: Keys can be disabled instantly without affecting other keys
- **Named**: Optional names for organization and tracking
- **One-Time Display**: Keys are shown only once for security

## Creating API Keys

### Via Settings Page

1. **Navigate to Settings**
   - Click "Settings" in the sidebar
   - Go to the "API Keys" section

2. **Select Agent**
   - Choose the agent you want to create a key for
   - Only agents in your organization are available

3. **Create Key**
   - Enter an optional name (e.g., "Production Integration", "n8n Workflow")
   - Click "Create Key"
   - **Important**: Copy the key immediately - you won't see it again!

### Via API

```bash
curl -X POST http://localhost:8000/v1/agents/agent_abc123/keys \
  -H "Authorization: Bearer your-token" \
  -H "X-Team-Id: your-org-id" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Integration Key"
  }'
```

**Response:**
```json
{
  "key_id": "key_def456",
  "api_key": "ak_live_abc123def456ghi789...",
  "name": "Production Integration Key",
  "created_at": "2025-01-18T10:00:00Z"
}
```

## Using API Keys

### Authentication Header

Use the `X-API-Key` header for authentication:

```bash
curl -X POST http://localhost:8000/v1/agents/agent_abc123/invoke \
  -H "X-API-Key: ak_live_abc123def456ghi789..." \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "help",
    "input": {
      "question": "How can I help you?"
    }
  }'
```

### Key Advantages

**No Team ID Required**: API keys automatically include organization context
**Simplified Auth**: No need for Bearer tokens or user authentication
**Tool-Friendly**: Perfect for automation tools and external integrations

## Managing Existing Keys

### Viewing Keys

The Settings page shows:
- **Key Name**: Your chosen name or "Unnamed Key"
- **Creation Date**: When the key was created
- **Key ID**: Unique identifier (not the actual key)
- **Actions**: Revoke button

**Security Note**: The actual API key is never displayed after creation.

### Revoking Keys

1. **Immediate Revocation**
   - Click "Revoke" next to any key
   - Key becomes invalid immediately
   - All requests using that key will fail

2. **Via API**
   ```bash
   curl -X DELETE http://localhost:8000/v1/agents/agent_abc123/keys/key_def456 \
     -H "Authorization: Bearer your-token" \
     -H "X-Team-Id: your-org-id"
   ```

## Security Best Practices

### Key Storage

**✅ Do:**
- Store keys in environment variables
- Use secure secret management systems
- Rotate keys regularly (monthly/quarterly)
- Use different keys for different environments

**❌ Don't:**
- Commit keys to version control
- Share keys in plain text (email, chat, etc.)
- Use the same key across multiple applications
- Store keys in client-side code

### Key Naming

Use descriptive names that indicate:
- **Purpose**: "Customer Support Bot", "Data Processing"
- **Environment**: "Production", "Staging", "Development"
- **Tool**: "n8n Workflow", "Make.com Scenario"
- **Team**: "Marketing Automation", "Support Team"

**Examples:**
- "Production - Customer Support n8n"
- "Staging - Data Processing Pipeline"
- "Dev - Testing Integration"

### Access Control

- **Principle of Least Privilege**: Create keys only for specific agents
- **Regular Audits**: Review and remove unused keys
- **Team Coordination**: Document which keys are used where
- **Incident Response**: Have a plan to quickly revoke compromised keys

## Integration Examples

### n8n HTTP Request Node

```json
{
  "method": "POST",
  "url": "http://localhost:8000/v1/agents/agent_abc123/invoke",
  "headers": {
    "X-API-Key": "ak_live_abc123def456...",
    "Content-Type": "application/json"
  },
  "body": {
    "capability": "help",
    "input": {
      "question": "{{$json.customer_question}}"
    }
  }
}
```

### Make.com HTTP Module

```json
{
  "url": "http://localhost:8000/v1/agents/agent_abc123/invoke",
  "method": "POST",
  "headers": [
    {
      "name": "X-API-Key",
      "value": "ak_live_abc123def456..."
    },
    {
      "name": "Content-Type",
      "value": "application/json"
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

### Python Application

```python
import os
import requests

API_KEY = os.getenv('COLLEXA_API_KEY')
AGENT_ID = 'agent_abc123'
BASE_URL = 'http://localhost:8000'

def invoke_agent(question):
    response = requests.post(
        f"{BASE_URL}/v1/agents/{AGENT_ID}/invoke",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "capability": "help",
            "input": {"question": question}
        }
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API call failed: {response.status_code}")

# Usage
result = invoke_agent("How do I reset my password?")
print(result)
```

## Troubleshooting

### Common Issues

**401 Unauthorized**
- Verify the API key is correct
- Check that the key hasn't been revoked
- Ensure you're using the `X-API-Key` header

**403 Forbidden**
- Verify the key belongs to the correct agent
- Check that the agent exists and is accessible
- Ensure you're in the correct organization

**Key Not Working After Creation**
- Double-check you copied the complete key
- Verify there are no extra spaces or characters
- Test with a simple echo capability first

### Testing API Keys

Use the echo capability to verify your key works:

```bash
curl -X POST http://localhost:8000/v1/agents/agent_abc123/invoke \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "echo",
    "input": {
      "test": "API key working"
    }
  }'
```

Expected response:
```json
{
  "agent_id": "agent_abc123",
  "status": "succeeded",
  "run_id": "run_xyz789",
  "result": {
    "echo": {
      "capability": "echo",
      "input": {
        "test": "API key working"
      }
    }
  }
}
```

## Key Rotation Strategy

### Regular Rotation

1. **Create New Key**: Generate replacement key with same name + date
2. **Update Applications**: Deploy new key to all integrations
3. **Test Thoroughly**: Verify all integrations work with new key
4. **Revoke Old Key**: Remove the previous key
5. **Document Change**: Update team documentation

### Emergency Rotation

If a key is compromised:
1. **Immediate Revocation**: Revoke the compromised key immediately
2. **Create Replacement**: Generate new key quickly
3. **Emergency Deployment**: Update critical applications first
4. **Monitor Systems**: Watch for any authentication failures
5. **Post-Incident Review**: Analyze how the compromise occurred

---

**Next**: [Monitoring & Analytics →](./monitoring.md)
