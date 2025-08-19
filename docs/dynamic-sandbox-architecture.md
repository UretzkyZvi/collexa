# Dynamic Sandbox Architecture Design

## 🎯 **Overview**

Replace the current static container approach with a dynamic, on-demand sandbox orchestration system that provides better scalability, customization, and resource efficiency.

## 🏗️ **Architecture Components**

### 1. Sandbox Orchestrator Service
**Purpose**: Manages the lifecycle of dynamic sandbox environments

**Key Responsibilities**:
- Create/destroy sandbox containers on-demand
- Allocate dynamic ports to avoid conflicts
- Generate custom OpenAPI specs per sandbox
- Track active sandboxes and their resources
- Handle cleanup and garbage collection

### 2. Configuration Template System
**Purpose**: Provides customizable mock service templates

**Features**:
- Base OpenAPI spec templates for each target system
- Jinja2 templating for dynamic customization
- Per-agent mock response overrides
- Support for custom endpoints and behaviors

### 3. Dynamic Container Management
**Purpose**: Docker-based container orchestration

**Capabilities**:
- Spin up Prism containers with custom specs
- Dynamic port allocation (45000+ range)
- Container health monitoring
- Automatic cleanup of unused containers

### 4. Service Registry
**Purpose**: Track active sandbox services and their endpoints

**Data Structure**:
```json
{
  "sandbox_id": "sb_123",
  "agent_id": "agent_456",
  "services": {
    "figma": {
      "container_id": "prism_figma_sb123",
      "port": 45001,
      "url": "http://localhost:45001",
      "status": "running",
      "spec_path": "/tmp/sb_123_figma.yaml"
    },
    "slack": {
      "container_id": "prism_slack_sb123", 
      "port": 45002,
      "url": "http://localhost:45002",
      "status": "running",
      "spec_path": "/tmp/sb_123_slack.yaml"
    }
  },
  "created_at": "2025-08-19T10:00:00Z",
  "last_accessed": "2025-08-19T10:30:00Z"
}
```

## 🔄 **API Design**

### Create Dynamic Sandbox
```http
POST /v1/agents/{agent_id}/sandboxes
Content-Type: application/json

{
  "required_services": ["figma", "slack"],
  "custom_configs": {
    "figma": {
      "workspace_name": "Agent Test Workspace",
      "mock_responses": {
        "/me": {
          "id": "custom_user_123",
          "email": "agent@example.com"
        }
      }
    },
    "slack": {
      "team_name": "Agent Testing Team",
      "channels": [
        {"id": "C123", "name": "general"},
        {"id": "C456", "name": "agent-testing"}
      ]
    }
  },
  "ttl_minutes": 60
}
```

**Response**:
```json
{
  "sandbox_id": "sb_789",
  "status": "creating",
  "services": {
    "figma": {
      "url": "http://localhost:45001",
      "status": "starting",
      "endpoints": ["/me", "/files/{key}", "/files/{key}/nodes"]
    },
    "slack": {
      "url": "http://localhost:45002", 
      "status": "starting",
      "endpoints": ["/auth.test", "/chat.postMessage", "/channels.list"]
    }
  },
  "proxy_url": "http://localhost:4000/sandbox/sb_789",
  "expires_at": "2025-08-19T11:00:00Z"
}
```

### Get Sandbox Status
```http
GET /v1/agents/{agent_id}/sandboxes/{sandbox_id}
```

### Update Sandbox Configuration
```http
PATCH /v1/agents/{agent_id}/sandboxes/{sandbox_id}
Content-Type: application/json

{
  "add_services": ["github"],
  "update_configs": {
    "figma": {
      "mock_responses": {
        "/files/ABC123": {
          "name": "Updated Design File"
        }
      }
    }
  }
}
```

### Delete Sandbox
```http
DELETE /v1/agents/{agent_id}/sandboxes/{sandbox_id}
```

## 🛠️ **Implementation Plan**

### Phase 1: Core Orchestrator
1. **SandboxOrchestrator Service** (`backend/app/services/sandbox_orchestrator.py`)
2. **Docker Integration** using `docker` Python library
3. **Port Management** with dynamic allocation
4. **Basic Template System** for OpenAPI specs

### Phase 2: Advanced Features  
1. **Custom Configuration Support** with Jinja2 templates
2. **Service Registry** with Redis/SQLite backend
3. **Health Monitoring** and auto-recovery
4. **Resource Limits** and quotas per agent

### Phase 3: Production Features
1. **Cleanup Automation** (TTL-based garbage collection)
2. **Metrics and Monitoring** (container resource usage)
3. **Load Balancing** for high-traffic scenarios
4. **Container Pooling** for faster startup times

## 📊 **Benefits of Dynamic Architecture**

| Aspect | Current Static | Proposed Dynamic |
|--------|---------------|------------------|
| **Resource Usage** | Always running 3+ containers | Only containers needed |
| **Customization** | Fixed responses | Per-agent custom responses |
| **Multi-System** | Separate sandboxes | Combined in one sandbox |
| **New Systems** | Infrastructure changes | Template addition only |
| **Isolation** | Shared responses | Isolated per sandbox |
| **Scalability** | Limited by pre-allocation | Scales with demand |

## 🔧 **Migration Strategy**

### Backward Compatibility
1. Keep current static containers running
2. Add feature flag: `USE_DYNAMIC_SANDBOXES=true/false`
3. Implement dynamic system alongside current
4. Gradually migrate existing sandboxes
5. Remove static containers once migration complete

### Configuration Migration
```python
# Convert static sandbox to dynamic
def migrate_static_to_dynamic(sandbox_id: str):
    static_config = get_static_sandbox_config(sandbox_id)
    dynamic_config = {
        "required_services": static_config["target_systems"],
        "custom_configs": generate_custom_configs(static_config),
        "ttl_minutes": 120  # Default TTL
    }
    return create_dynamic_sandbox(dynamic_config)
```

## 🎯 **Success Metrics**

- **Resource Efficiency**: 70% reduction in idle container resources
- **Customization**: 100% of sandboxes can have custom mock responses  
- **Multi-System Support**: Agents can use 2+ services in one sandbox
- **Startup Time**: New sandboxes ready in <30 seconds
- **Cleanup**: Automatic removal of unused sandboxes within TTL

This dynamic architecture provides the flexibility and scalability needed for a production-ready agent sandbox system.
