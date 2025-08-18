# Core Concepts

Understanding these fundamental concepts will help you make the most of the Collexa platform.

## Agents

### What is an Agent?

An **Agent** is an AI-powered entity that can perform specific tasks and respond to requests. Each agent has:

- **Unique Identity**: Agent ID and display name
- **Capabilities**: Specific functions it can perform
- **Context**: Understanding of its purpose and domain
- **Endpoints**: API URLs for interaction

### Agent Lifecycle

```mermaid
graph LR
    A[Create] --> B[Configure]
    B --> C[Test]
    C --> D[Deploy]
    D --> E[Monitor]
    E --> F[Optimize]
    F --> C
```

1. **Create**: Define agent purpose with a brief description
2. **Configure**: Set up capabilities and parameters
3. **Test**: Validate functionality through playground or API
4. **Deploy**: Integrate with external tools and workflows
5. **Monitor**: Track performance and usage metrics
6. **Optimize**: Improve based on feedback and analytics

## Organizations & Teams

### Multi-Tenant Architecture

Collexa uses a **multi-tenant architecture** where:

- **Organizations**: Top-level containers for teams and resources
- **Team Isolation**: Complete data separation between organizations
- **User Management**: Users can belong to multiple organizations
- **Resource Scoping**: Agents, API keys, and logs are org-specific

### Organization Structure

```
Organization: "Acme Corp"
├── Agents
│   ├── Customer Support Agent
│   ├── Sales Assistant
│   └── Technical Documentation Bot
├── API Keys
│   ├── Production Key (Customer Support)
│   └── Development Key (Testing)
├── Users
│   ├── admin@acme.com (Owner)
│   ├── dev@acme.com (Developer)
│   └── support@acme.com (User)
└── Audit Logs
    ├── API Calls
    ├── Agent Invocations
    └── User Actions
```

## Authentication & Security

### Authentication Methods

1. **Bearer Tokens** (Dashboard/Web)
   ```bash
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
   X-Team-Id: org_abc123
   ```

2. **API Keys** (External Integrations)
   ```bash
   X-API-Key: ak_live_abc123def456...
   # No X-Team-Id required - scoped to agent+org
   ```

### Security Model

- **Row-Level Security (RLS)**: Database-level tenant isolation
- **API Key Scoping**: Keys are bound to specific agent+organization
- **Audit Logging**: All API calls and user actions are logged
- **HTTPS Only**: All communication encrypted in transit
- **Secret Management**: Sensitive data hashed and secured

## Capabilities & Invocations

### What are Capabilities?

**Capabilities** define what an agent can do. Each capability:

- Has a unique name (e.g., "help", "analyze", "generate")
- Accepts structured input data
- Returns structured output data
- Can be invoked via API or dashboard

### Default Capabilities

Every agent includes these built-in capabilities:

| Capability | Purpose | Input | Output |
|------------|---------|-------|--------|
| `help` | General assistance | `{"question": "string"}` | Helpful response |
| `echo` | Testing/debugging | `{any: "data"}` | Echoes input back |
| `status` | Health check | `{}` | Agent status info |

### Invocation Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Agent
    participant Database
    
    Client->>API: POST /v1/agents/{id}/invoke
    API->>Database: Create Run record
    API->>Agent: Process capability
    Agent->>Database: Log execution steps
    Agent->>API: Return result
    API->>Database: Update Run status
    API->>Client: Return response
```

## Runs & Logs

### Execution Tracking

Every agent invocation creates a **Run**:

- **Run ID**: Unique identifier for the execution
- **Status**: queued → running → succeeded/failed
- **Input/Output**: Request data and response
- **Logs**: Detailed execution steps and timing
- **Metadata**: Agent, organization, user, timestamps

### Log Structure

```json
{
  "run_id": "run_xyz789",
  "agent_id": "agent_abc123",
  "org_id": "org_def456",
  "status": "succeeded",
  "input": {
    "capability": "help",
    "input": {"question": "How do I...?"}
  },
  "output": {
    "result": "Here's how you can..."
  },
  "logs": [
    {
      "timestamp": "2025-01-18T10:00:01Z",
      "level": "info",
      "message": "Processing capability: help"
    }
  ],
  "created_at": "2025-01-18T10:00:00Z",
  "completed_at": "2025-01-18T10:00:02Z"
}
```

## API Keys

### Key Types & Scoping

- **Agent-Scoped**: Keys are tied to specific agent+organization
- **Secure Storage**: Keys are hashed using SHA-256
- **Revocable**: Keys can be disabled without affecting others
- **Named**: Optional names for organization and tracking

### Key Management

```bash
# Create key
POST /v1/agents/{agent_id}/keys
{
  "name": "Production Integration"
}

# List keys (returns metadata only, not actual keys)
GET /v1/agents/{agent_id}/keys

# Revoke key
DELETE /v1/agents/{agent_id}/keys/{key_id}
```

## Observability

### Metrics Collection

Collexa automatically tracks:

- **API Calls**: Total requests, success rate, error count
- **Latency**: Response times with percentile breakdowns
- **Agent Performance**: Invocation count and duration
- **System Health**: Resource usage and availability

### Monitoring Dashboard

Real-time metrics include:

- **Request Volume**: API calls over time
- **Performance**: P50, P95, P99 latency percentiles
- **Success Rate**: Percentage of successful operations
- **Error Analysis**: Error types and frequency

### Structured Logging

All logs include contextual information:

```json
{
  "timestamp": "2025-01-18T10:00:00Z",
  "level": "info",
  "message": "Agent invocation completed",
  "request_id": "req_abc123",
  "org_id": "org_def456",
  "agent_id": "agent_xyz789",
  "duration_ms": 1250,
  "status_code": 200
}
```

## Integration Patterns

### Common Integration Scenarios

1. **Workflow Automation** (n8n, Make.com)
   - Trigger agents from workflow events
   - Process data and return results
   - Chain multiple agents together

2. **Custom Applications**
   - Embed AI capabilities in your apps
   - Real-time or batch processing
   - User-facing or background tasks

3. **API Orchestration**
   - Combine multiple services
   - Add AI decision-making to pipelines
   - Transform and enrich data

### Best Practices

- **Error Handling**: Always check response status
- **Rate Limiting**: Respect API limits and implement backoff
- **Security**: Store API keys securely, rotate regularly
- **Monitoring**: Track usage and performance metrics
- **Testing**: Use echo capability for integration testing

## Data Flow

### Request Processing

```mermaid
graph TD
    A[Client Request] --> B[Authentication]
    B --> C[Rate Limiting]
    C --> D[Input Validation]
    D --> E[Agent Invocation]
    E --> F[Capability Processing]
    F --> G[Response Generation]
    G --> H[Audit Logging]
    H --> I[Metrics Collection]
    I --> J[Client Response]
```

### Data Storage

- **PostgreSQL**: Primary data store with RLS
- **Structured Data**: JSON columns for flexible schemas
- **Audit Trail**: Immutable log records
- **Metrics**: Time-series data for analytics

---

**Next Steps:**
- **[User Guide](../user-guide/dashboard.md)** - Explore platform features
- **[Integration Guides](../integrations/overview.md)** - Connect external tools
- **[API Reference](../api/overview.md)** - Complete API documentation
