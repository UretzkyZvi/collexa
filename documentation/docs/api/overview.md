# API Reference Overview

The Collexa API provides programmatic access to all platform features. This RESTful API uses JSON for data exchange and supports both API key and Bearer token authentication.

## Base URL

**Development**: `http://localhost:8000`
**Production**: `https://api.yourdomain.com`

All API endpoints are prefixed with `/v1/`:
```
https://api.yourdomain.com/v1/agents
```

## Authentication

Collexa supports two authentication methods:

### API Keys (Recommended for Integrations)

API keys provide scoped access to specific agents without user authentication:

```bash
curl -X POST https://api.yourdomain.com/v1/agents/agent_abc123/invoke \
  -H "X-API-Key: ak_live_abc123def456..." \
  -H "Content-Type: application/json"
```

**Benefits:**
- No user authentication required
- Scoped to specific agent and organization
- Perfect for external tools (n8n, Make.com, etc.)
- Easy to manage and rotate

### Bearer Tokens (For User Applications)

Bearer tokens provide full access to user's organization:

```bash
curl -X POST https://api.yourdomain.com/v1/agents/agent_abc123/invoke \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "X-Team-Id: org_abc123" \
  -H "Content-Type: application/json"
```

**Benefits:**
- Full access to user's resources
- User context and permissions
- Suitable for user-facing applications

## Request Format

### Content Type

All requests must include the `Content-Type` header:
```
Content-Type: application/json
```

### Request Body

Request bodies must be valid JSON:
```json
{
  "capability": "help",
  "input": {
    "question": "How can I help you?"
  }
}
```

### URL Parameters

Some endpoints accept URL parameters:
```
GET /v1/runs?limit=50&status=succeeded&agent_id=agent_abc123
```

## Response Format

### Success Response

Successful responses return JSON with appropriate HTTP status codes:

```json
{
  "agent_id": "agent_abc123",
  "status": "succeeded",
  "run_id": "run_xyz789",
  "result": {
    "response": "Generated response content"
  }
}
```

### Error Response

Error responses include error details and HTTP status codes:

```json
{
  "error": {
    "type": "authentication_error",
    "message": "Invalid API key",
    "code": "INVALID_API_KEY",
    "details": {
      "provided_key": "ak_live_invalid..."
    }
  },
  "request_id": "req_abc123"
}
```

## HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request format or parameters |
| 401 | Unauthorized | Authentication failed |
| 403 | Forbidden | Access denied |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

## Rate Limiting

API requests are rate limited to ensure fair usage:

- **Default Limit**: 1000 requests per hour per organization
- **Burst Limit**: 100 requests per minute
- **Headers**: Rate limit information in response headers

**Rate Limit Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642694400
```

**Rate Limit Exceeded Response:**
```json
{
  "error": {
    "type": "rate_limit_error",
    "message": "Rate limit exceeded",
    "code": "RATE_LIMIT_EXCEEDED",
    "details": {
      "limit": 1000,
      "reset_time": "2025-01-18T11:00:00Z"
    }
  }
}
```

## Pagination

List endpoints support pagination using cursor-based pagination:

**Request:**
```bash
GET /v1/runs?limit=50&cursor=eyJjcmVhdGVkX2F0IjoiMjAyNS0wMS0xOCJ9
```

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "has_more": true,
    "next_cursor": "eyJjcmVhdGVkX2F0IjoiMjAyNS0wMS0xOCJ9",
    "limit": 50
  }
}
```

## Request IDs

Every API request receives a unique request ID for tracking and debugging:

**Response Header:**
```
X-Request-ID: req_abc123def456
```

**Error Response:**
```json
{
  "error": {...},
  "request_id": "req_abc123def456"
}
```

Use request IDs when reporting issues or debugging problems.

## Idempotency

Some endpoints support idempotency to safely retry requests:

**Idempotent Request:**
```bash
curl -X POST https://api.yourdomain.com/v1/agents \
  -H "Idempotency-Key: unique-key-123" \
  -H "Authorization: Bearer token" \
  -d '{"brief": "Customer support agent"}'
```

**Benefits:**
- Safe to retry failed requests
- Prevents duplicate resource creation
- Consistent behavior across retries

## Webhooks

Collexa can send webhook notifications for events:

**Webhook Payload:**
```json
{
  "event": "agent.invocation.completed",
  "data": {
    "agent_id": "agent_abc123",
    "run_id": "run_xyz789",
    "status": "succeeded",
    "timestamp": "2025-01-18T10:00:00Z"
  },
  "webhook_id": "wh_abc123"
}
```

## SDKs and Libraries

### Official SDKs

- **Python**: `pip install collexa-python`
- **JavaScript/Node.js**: `npm install collexa-js`
- **TypeScript**: Built-in TypeScript support

### Community Libraries

- **Go**: `go get github.com/collexa/collexa-go`
- **Ruby**: `gem install collexa-ruby`
- **PHP**: `composer require collexa/collexa-php`

### Example Usage

**Python:**
```python
from collexa import Client

client = Client(api_key="ak_live_...")
result = client.agents.invoke(
    agent_id="agent_abc123",
    capability="help",
    input={"question": "Hello world"}
)
```

**JavaScript:**
```javascript
import { Collexa } from 'collexa-js';

const client = new Collexa({ apiKey: 'ak_live_...' });
const result = await client.agents.invoke({
  agentId: 'agent_abc123',
  capability: 'help',
  input: { question: 'Hello world' }
});
```

## OpenAPI Specification

The complete API specification is available in OpenAPI 3.0 format:

**Download:**
- **JSON**: `GET /v1/openapi.json`
- **YAML**: `GET /v1/openapi.yaml`

**Interactive Documentation:**
- **Swagger UI**: `GET /docs`
- **ReDoc**: `GET /redoc`

## Testing

### Test Environment

Use the test environment for development:
- **Base URL**: `https://api-test.yourdomain.com`
- **Test API Keys**: Prefixed with `ak_test_`
- **No Rate Limits**: For development convenience

### Example Requests

**Test Agent Creation:**
```bash
curl -X POST https://api-test.yourdomain.com/v1/agents \
  -H "Authorization: Bearer test_token" \
  -H "X-Team-Id: test_org" \
  -H "Content-Type: application/json" \
  -d '{"brief": "Test agent for development"}'
```

**Test Agent Invocation:**
```bash
curl -X POST https://api-test.yourdomain.com/v1/agents/agent_test123/invoke \
  -H "X-API-Key: ak_test_123456..." \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "echo",
    "input": {"test": "Hello world"}
  }'
```

## Best Practices

### Error Handling

Always check response status codes and handle errors appropriately:

```python
import requests

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    result = response.json()
    # Handle success
elif response.status_code == 401:
    # Handle authentication error
elif response.status_code == 429:
    # Handle rate limiting
else:
    # Handle other errors
    error = response.json()
    print(f"Error: {error['error']['message']}")
```

### Retry Logic

Implement exponential backoff for retries:

```python
import time
import random

def make_request_with_retry(url, headers, data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 429:
                # Rate limited, wait and retry
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
                continue
            return response
        except requests.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
```

### Security

1. **Store API Keys Securely**: Use environment variables or secret managers
2. **Use HTTPS**: Always use encrypted connections
3. **Validate Responses**: Check response format and content
4. **Log Appropriately**: Don't log sensitive data

---

**Next**: Explore specific API endpoints:
- **[Authentication →](./authentication.md)**
- **[Agents API →](./agents.md)**
- **[Invocations API →](./invocations.md)**
- **[Logs API →](./logs.md)**
