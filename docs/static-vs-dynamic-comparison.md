# Static vs Dynamic Sandbox Architecture Comparison

## 🔍 **Current Static Architecture Issues**

### Resource Inefficiency
```yaml
# Current: Always running regardless of usage
services:
  prism-figma:    # 🔴 Always consuming resources
  prism-slack:    # 🔴 Always consuming resources  
  prism-generic:  # 🔴 Always consuming resources
  nginx-proxy:    # 🔴 Always consuming resources
```

**Problems:**
- 4 containers running 24/7 even when no agents are testing
- Fixed memory/CPU allocation regardless of demand
- Port conflicts when scaling (fixed ports 4010-4012)

### Limited Customization
```http
# Current: All agents get same responses
GET /sandbox/agent1/figma/me
GET /sandbox/agent2/figma/me
# Both return identical mock user data
```

**Problems:**
- No per-agent customization of mock responses
- Fixed OpenAPI specs can't be tailored to use cases
- All agents share the same "workspace" context

### Scalability Constraints
```bash
# Adding new system requires infrastructure changes
1. Create new OpenAPI spec file
2. Add new container to docker-compose.yml
3. Update nginx routing configuration
4. Restart entire infrastructure
```

**Problems:**
- Infrastructure changes needed for each new target system
- No support for agents needing multiple systems simultaneously
- Manual scaling and configuration management

## 🚀 **Proposed Dynamic Architecture Benefits**

### On-Demand Resource Allocation
```http
POST /v1/agents/agent123/sandboxes/dynamic
{
  "required_services": ["figma", "slack"],
  "ttl_minutes": 60
}

# Response: Only creates containers for requested services
{
  "services": {
    "figma": {"url": "http://localhost:45001", "status": "running"},
    "slack": {"url": "http://localhost:45002", "status": "running"}
  }
}
```

**Benefits:**
- ✅ Containers created only when needed
- ✅ Automatic cleanup after TTL expires
- ✅ Dynamic port allocation prevents conflicts
- ✅ Resource usage scales with actual demand

### Per-Agent Customization
```http
POST /v1/agents/agent123/sandboxes/dynamic
{
  "required_services": ["figma"],
  "custom_configs": {
    "figma": {
      "workspace_name": "Agent UX Testing",
      "mock_responses": {
        "/me": {
          "id": "agent_user_123",
          "email": "ux-agent@company.com",
          "handle": "ux_testing_agent"
        },
        "/files/ABC123": {
          "name": "Mobile App Wireframes",
          "role": "editor"
        }
      }
    }
  }
}
```

**Benefits:**
- ✅ Custom mock responses per agent
- ✅ Tailored workspace configurations
- ✅ Agent-specific test scenarios
- ✅ Isolated testing environments

### Multi-System Support
```http
POST /v1/agents/agent456/sandboxes/dynamic
{
  "required_services": ["figma", "slack", "github"],
  "custom_configs": {
    "figma": {"workspace_name": "Design System Updates"},
    "slack": {"team_name": "Design Team", "channels": ["#design-system"]},
    "github": {"repo": "company/design-system", "branch": "feature/tokens"}
  }
}
```

**Benefits:**
- ✅ Multiple services in one sandbox
- ✅ Cross-system integration testing
- ✅ Realistic workflow simulation
- ✅ Coordinated mock responses across systems

### Easy Extensibility
```python
# Adding new system: Just add template
class NewSystemTemplate:
    def generate_spec(self, custom_config):
        return render_template("new_system.yaml.j2", custom_config)

# No infrastructure changes needed!
```

**Benefits:**
- ✅ New systems added via templates only
- ✅ No container orchestration changes
- ✅ Plugin-like architecture
- ✅ Community contributions possible

## 📊 **Performance Comparison**

| Metric | Static Architecture | Dynamic Architecture |
|--------|-------------------|---------------------|
| **Idle Resource Usage** | 4 containers always running | 0 containers when idle |
| **Startup Time** | Instant (already running) | ~30 seconds (container creation) |
| **Memory Usage** | ~400MB baseline | Scales with usage |
| **Port Management** | Fixed ports (conflicts) | Dynamic allocation |
| **Customization** | None | Full per-sandbox |
| **Multi-System** | Separate sandboxes | Combined in one |
| **Cleanup** | Manual | Automatic (TTL-based) |

## 🔄 **Migration Path**

### Phase 1: Parallel Implementation
```python
# Feature flag approach
USE_DYNAMIC_SANDBOXES = os.getenv("USE_DYNAMIC_SANDBOXES", "false").lower() == "true"

if USE_DYNAMIC_SANDBOXES:
    return await create_dynamic_sandbox(agent_id, request)
else:
    return await create_static_sandbox(agent_id, request)
```

### Phase 2: Gradual Migration
```python
# Migrate existing sandboxes
async def migrate_static_to_dynamic():
    for sandbox in get_static_sandboxes():
        dynamic_config = convert_static_config(sandbox)
        new_sandbox = await orchestrator.create_sandbox(
            sandbox.agent_id, 
            dynamic_config
        )
        await cleanup_static_sandbox(sandbox.id)
```

### Phase 3: Complete Transition
```bash
# Remove static infrastructure
docker-compose -f docker-compose.sandbox.yml down
rm docker-compose.sandbox.yml
rm -rf sandbox-specs/static/
```

## 🎯 **Recommended Implementation Strategy**

### Immediate Actions
1. **Implement Dynamic Orchestrator** (already created)
2. **Add Feature Flag** for switching between modes
3. **Create Template System** for OpenAPI spec generation
4. **Update Frontend** to support dynamic sandbox creation

### Short-term Goals (1-2 weeks)
1. **Template System**: Convert static specs to Jinja2 templates
2. **Port Management**: Implement dynamic port allocation
3. **Health Monitoring**: Add container health checks
4. **Basic Cleanup**: TTL-based garbage collection

### Long-term Goals (1 month)
1. **Advanced Templates**: Support for complex customizations
2. **Resource Limits**: Per-agent quotas and limits
3. **Metrics**: Container resource usage monitoring
4. **Load Balancing**: Handle high-traffic scenarios

## 💡 **Key Insights**

### Why Dynamic is Better
1. **Resource Efficiency**: Only use what you need
2. **Flexibility**: Customize everything per use case
3. **Scalability**: Add new systems without infrastructure changes
4. **Isolation**: True per-agent sandbox environments
5. **Maintenance**: Automatic cleanup and management

### Migration Benefits
1. **Backward Compatibility**: Keep existing functionality during transition
2. **Risk Mitigation**: Gradual rollout with feature flags
3. **Learning Opportunity**: Understand usage patterns before full migration
4. **User Feedback**: Gather input on dynamic features

The dynamic architecture addresses all the scalability and flexibility concerns while providing a clear migration path from the current static implementation.
