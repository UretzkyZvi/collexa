# J.1 OPA Policy Engine Scaffold

This document describes the J.1 implementation: OPA (Open Policy Agent) integration for policy-based access control on agent invocations.

## Overview

J.1 provides a scaffold for policy enforcement using OPA, implementing:
- OPA container in development stack
- Policy bundle structure per organization
- Python client wrapper for policy evaluation
- Middleware hook for pre-invoke capability checks
- Unit tests for allow/deny scenarios

## Components

### 1. OPA Container (`docker-compose.dev.yml`)
- OPA server running on port 8181
- Mounts policy files from `backend/policies/`
- Health check endpoint at `/health`
- Decision logging enabled for debugging

### 2. Policy Structure (`backend/policies/`)
- **`collexa/authz/invoke.rego`**: Main authorization policy for agent invocations
- **`data.json`**: Static policy data (org owners, user permissions)
- Policies support org-based access control and capability-specific permissions

### 3. Python OPA Client (`backend/app/security/opa.py`)
- `OPAPolicyEngine`: Async HTTP client for OPA evaluation
- `can_invoke_capability()`: High-level method for capability authorization
- `evaluate_policy()`: Low-level policy evaluation
- Fail-closed security model (deny on errors)

### 4. Policy Middleware (`backend/app/middleware/policy_middleware.py`)
- `PolicyEnforcementMiddleware`: Intercepts agent invoke requests
- Extracts capability from request body
- Evaluates policy before allowing request to proceed
- Structured logging for policy decisions

### 5. Development Scripts
- **`scripts/dev-opa.ps1`**: Start OPA container with policies
- **`scripts/dev-all.ps1`**: Start full development stack (TODO)

## Configuration

### Environment Variables (`.env`)
```bash
# OPA server URL for policy evaluation
OPA_URL=http://localhost:8181
```

### Dependencies (`requirements.txt`)
```
httpx>=0.27,<1.0  # HTTP client for OPA integration
pytest-asyncio   # Async test support
```

## Usage

### 1. Start OPA Server
```powershell
.\scripts\dev-opa.ps1
```

### 2. Enable Policy Middleware
Uncomment in `backend/app/main.py`:
```python
app.add_middleware(PolicyEnforcementMiddleware)
```

### 3. Test Policy Evaluation
```bash
curl -X POST http://localhost:8181/v1/data/collexa/authz/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "user": {"id": "u1"},
      "org": {"id": "o1"},
      "agent": {"id": "agent-1"},
      "capability": "test_capability"
    }
  }'
```

## Policy Rules

The default policy (`invoke.rego`) implements:

1. **Org Owner Access**: Users who own the organization can invoke any capability
2. **Explicit Permissions**: Users with explicit capability permissions can invoke
3. **Read-Only Access**: Capabilities starting with "get", "list", or "read" are allowed
4. **Default Deny**: All other requests are denied

## Testing

### Unit Tests
- `tests/test_opa_integration.py`: OPA client functionality
- `tests/test_policy_middleware.py`: Middleware integration

### Test Data
The `data.json` file contains test users and permissions:
- `u1` (org owner of `o1`): Full access
- `u2`: Read-only access
- `test-user`: Limited capability access

## Security Model

- **Fail Closed**: Policy evaluation errors result in access denial
- **Request Context**: Policies receive user, org, agent, and capability context
- **Audit Logging**: All policy decisions are logged with structured data
- **Isolation**: Policies are evaluated per-request with no shared state

## Future Enhancements

1. **Dynamic Policy Loading**: Load policies from database per organization
2. **Policy Versioning**: Support policy updates without service restart
3. **Advanced RBAC**: Role-based access control with hierarchical permissions
4. **Policy Testing**: Built-in policy testing framework
5. **Performance**: Policy result caching for frequently accessed capabilities

## Status

- ✅ OPA container and policy structure
- ✅ Python client wrapper with async support
- ✅ Policy middleware with request interception
- ✅ Unit tests for core functionality
- ⚠️ Middleware currently disabled (enable when OPA is configured)
- 🔄 Integration with existing auth system
- 🔄 Production-ready policy management
