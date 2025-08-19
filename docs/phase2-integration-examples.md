# Phase 2 Integration Examples & Code Stubs

## Overview

This document provides FastAPI endpoint examples and minimal integration code for high-priority Phase 2 libraries. All examples assume our existing tech stack and follow established patterns from Phase 1.

---

## Milestone H — MCP Protocol Integration

### MCP Server Setup with modelcontextprotocol/python

```python
# backend/app/mcp/server.py
from mcp import Server, Tool
from mcp.types import TextContent, CallToolResult
from fastapi import WebSocket
import json

class AgentMCPServer:
    def __init__(self, agent_id: str, capabilities: list[str]):
        self.agent_id = agent_id
        self.server = Server("collexa-agent")
        self._register_tools(capabilities)
    
    def _register_tools(self, capabilities: list[str]):
        for capability in capabilities:
            tool = Tool(
                name=capability,
                description=f"Execute {capability} for agent {self.agent_id}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "input": {"type": "object"}
                    }
                }
            )
            self.server.add_tool(tool, self._handle_tool_call)
    
    async def _handle_tool_call(self, name: str, arguments: dict) -> CallToolResult:
        # Delegate to existing agent invoke logic
        from app.services.agent_service import invoke_agent_capability
        
        result = await invoke_agent_capability(
            agent_id=self.agent_id,
            capability=name,
            input_data=arguments.get("input", {})
        )
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result))]
        )

# FastAPI WebSocket endpoint
@app.websocket("/mcp/{agent_id}")
async def mcp_websocket(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    
    # Get agent capabilities from database
    agent = await get_agent_by_id(agent_id)
    if not agent:
        await websocket.close(code=4004)
        return
    
    mcp_server = AgentMCPServer(agent_id, agent.capabilities)
    
    try:
        async for message in websocket.iter_text():
            request = json.loads(message)
            response = await mcp_server.server.handle_request(request)
            await websocket.send_text(json.dumps(response))
    except Exception as e:
        logger.error(f"MCP WebSocket error: {e}")
        await websocket.close(code=1011)
```

### Manifest Signing with python-jose

```python
# backend/app/services/manifest_service.py
from jose import jws
from jose.constants import ALGORITHMS
import json
from datetime import datetime, timezone

class ManifestSigner:
    def __init__(self, private_key: str, key_id: str):
        self.private_key = private_key
        self.key_id = key_id
    
    def sign_manifest(self, agent_id: str, capabilities: list[dict]) -> dict:
        manifest = {
            "agent_id": agent_id,
            "version": "1.0",
            "capabilities": capabilities,
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "issuer": "collexa-platform"
        }
        
        headers = {
            "alg": "ES256",
            "kid": self.key_id,
            "typ": "JWT"
        }
        
        signature = jws.sign(
            payload=json.dumps(manifest),
            key=self.private_key,
            algorithm=ALGORITHMS.ES256,
            headers=headers
        )
        
        return {
            "manifest": manifest,
            "signature": signature,
            "key_id": self.key_id
        }
    
    @staticmethod
    def verify_manifest(signed_manifest: str, public_key: str) -> dict:
        try:
            payload = jws.verify(
                token=signed_manifest,
                key=public_key,
                algorithms=[ALGORITHMS.ES256]
            )
            return json.loads(payload)
        except Exception as e:
            raise ValueError(f"Invalid manifest signature: {e}")

# FastAPI endpoint
@app.post("/v1/agents/{agent_id}/manifests")
async def create_agent_manifest(
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    agent = await get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    signer = ManifestSigner(
        private_key=settings.MANIFEST_PRIVATE_KEY,
        key_id=settings.MANIFEST_KEY_ID
    )
    
    signed_manifest = signer.sign_manifest(
        agent_id=agent_id,
        capabilities=agent.capabilities
    )
    
    # Store in database
    await store_manifest(agent_id, signed_manifest)
    
    return signed_manifest
```

---

## Milestone J — OPA Policy Integration

### OPA Policy Evaluation

```python
# backend/app/services/policy_service.py
import httpx
from typing import Dict, Any

class OPAPolicyEngine:
    def __init__(self, opa_url: str = "http://localhost:8181"):
        self.opa_url = opa_url
        self.client = httpx.AsyncClient()
    
    async def evaluate_policy(
        self,
        policy_path: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate OPA policy with input data"""
        url = f"{self.opa_url}/v1/data/{policy_path}"
        
        response = await self.client.post(
            url,
            json={"input": input_data},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise Exception(f"OPA evaluation failed: {response.text}")
        
        return response.json()
    
    async def can_invoke_capability(
        self,
        user_id: str,
        org_id: str,
        agent_id: str,
        capability: str,
        context: Dict[str, Any] = None
    ) -> bool:
        """Check if user can invoke a specific capability"""
        input_data = {
            "user": {"id": user_id},
            "org": {"id": org_id},
            "agent": {"id": agent_id},
            "capability": capability,
            "context": context or {}
        }
        
        result = await self.evaluate_policy("collexa/authz/invoke", input_data)
        return result.get("result", {}).get("allow", False)

# FastAPI middleware for policy enforcement
@app.middleware("http")
async def policy_enforcement_middleware(request: Request, call_next):
    # Skip policy check for public endpoints
    if request.url.path.startswith("/health"):
        return await call_next(request)
    
    # Extract auth context
    user = getattr(request.state, "user", None)
    if not user:
        return await call_next(request)
    
    # Check if this is an agent invoke request
    if request.method == "POST" and "/agents/" in request.url.path and "/invoke" in request.url.path:
        agent_id = request.path_params.get("agent_id")
        
        # Get capability from request body
        body = await request.body()
        try:
            data = json.loads(body)
            capability = data.get("capability")
        except:
            capability = None
        
        if agent_id and capability:
            policy_engine = OPAPolicyEngine()
            allowed = await policy_engine.can_invoke_capability(
                user_id=user.id,
                org_id=user.org_id,
                agent_id=agent_id,
                capability=capability
            )
            
            if not allowed:
                return JSONResponse(
                    status_code=403,
                    content={"error": "Policy denied access to capability"}
                )
    
    return await call_next(request)
```

### Simple Approval Workflow with transitions

```python
# backend/app/models/approval.py
from transitions import Machine
from sqlalchemy import Column, String, DateTime, Text, Enum
from app.database import Base
import enum

class ApprovalStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"

class Approval(Base):
    __tablename__ = "approvals"
    
    id = Column(String, primary_key=True)
    org_id = Column(String, nullable=False)
    subject_type = Column(String, nullable=False)  # "agent_invoke", "budget_override"
    subject_id = Column(String, nullable=False)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    approver_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime)
    context = Column(Text)  # JSON
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Setup state machine
        states = ['pending', 'approved', 'denied', 'expired']
        transitions = [
            {'trigger': 'approve', 'source': 'pending', 'dest': 'approved'},
            {'trigger': 'deny', 'source': 'pending', 'dest': 'denied'},
            {'trigger': 'expire', 'source': 'pending', 'dest': 'expired'},
        ]
        
        self.machine = Machine(
            model=self,
            states=states,
            transitions=transitions,
            initial='pending'
        )

# FastAPI endpoints
@app.post("/v1/approvals")
async def create_approval(
    approval_data: dict,
    current_user: User = Depends(get_current_user)
):
    approval = Approval(
        org_id=current_user.org_id,
        subject_type=approval_data["subject_type"],
        subject_id=approval_data["subject_id"],
        context=json.dumps(approval_data.get("context", {}))
    )
    
    db.add(approval)
    await db.commit()
    
    # Send notification to approvers
    await notify_approvers(approval)
    
    return {"approval_id": approval.id, "status": approval.status.value}

@app.post("/v1/approvals/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    current_user: User = Depends(get_current_user)
):
    approval = await get_approval_by_id(approval_id)
    if not approval:
        raise HTTPException(404, "Approval not found")
    
    # Check if user can approve
    if not await can_user_approve(current_user, approval):
        raise HTTPException(403, "Not authorized to approve")
    
    approval.approve()
    approval.approver_id = current_user.id
    approval.decided_at = datetime.utcnow()
    
    await db.commit()
    
    # Execute the approved action
    await execute_approved_action(approval)
    
    return {"status": "approved"}
```

---

## Milestone N — Sandbox Container Integration

### Testcontainers for Sandbox Management

```python
# backend/app/services/sandbox_service.py
from testcontainers.generic import GenericContainer
from testcontainers.postgres import PostgresContainer
import docker
import json
from typing import Dict, Any, Optional

class SandboxManager:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.active_sandboxes: Dict[str, GenericContainer] = {}
    
    async def create_sandbox(
        self,
        sandbox_id: str,
        target_system: str,
        mode: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new sandbox environment"""
        
        if mode == "mock":
            return await self._create_mock_sandbox(sandbox_id, target_system, config)
        elif mode == "emulated":
            return await self._create_emulated_sandbox(sandbox_id, target_system, config)
        elif mode == "connected":
            return await self._create_connected_sandbox(sandbox_id, target_system, config)
        else:
            raise ValueError(f"Unknown sandbox mode: {mode}")
    
    async def _create_mock_sandbox(
        self,
        sandbox_id: str,
        target_system: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create mock sandbox with recorded responses"""
        
        # Use Prism for API mocking
        container = GenericContainer("stoplight/prism:4")
        container.with_command(f"mock -h 0.0.0.0 /openapi/{target_system}.yaml")
        container.with_bind_ports(4010, 4010)
        container.with_volume_mapping(
            f"./sandbox-specs/{target_system}",
            "/openapi",
            "ro"
        )
        
        container.start()
        self.active_sandboxes[sandbox_id] = container
        
        return {
            "sandbox_id": sandbox_id,
            "mode": "mock",
            "endpoint": f"http://localhost:{container.get_exposed_port(4010)}",
            "status": "running"
        }
    
    async def _create_emulated_sandbox(
        self,
        sandbox_id: str,
        target_system: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create emulated sandbox with local database"""
        
        # Start a PostgreSQL container for emulated data
        postgres = PostgresContainer("postgres:15")
        postgres.start()
        
        # Start application container with emulated backend
        app_container = GenericContainer(f"collexa/sandbox-{target_system}:latest")
        app_container.with_env("DATABASE_URL", postgres.get_connection_url())
        app_container.with_env("MODE", "emulated")
        app_container.with_bind_ports(8080, 8080)
        
        app_container.start()
        
        self.active_sandboxes[f"{sandbox_id}-db"] = postgres
        self.active_sandboxes[sandbox_id] = app_container
        
        return {
            "sandbox_id": sandbox_id,
            "mode": "emulated",
            "endpoint": f"http://localhost:{app_container.get_exposed_port(8080)}",
            "database_url": postgres.get_connection_url(),
            "status": "running"
        }
    
    async def stop_sandbox(self, sandbox_id: str) -> bool:
        """Stop and remove sandbox"""
        if sandbox_id in self.active_sandboxes:
            container = self.active_sandboxes[sandbox_id]
            container.stop()
            del self.active_sandboxes[sandbox_id]
            return True
        return False
    
    async def reset_sandbox(self, sandbox_id: str) -> bool:
        """Reset sandbox to initial state"""
        # Stop current sandbox
        await self.stop_sandbox(sandbox_id)
        
        # Recreate with same config (stored in database)
        sandbox_config = await get_sandbox_config(sandbox_id)
        if sandbox_config:
            await self.create_sandbox(
                sandbox_id,
                sandbox_config["target_system"],
                sandbox_config["mode"],
                sandbox_config["config"]
            )
            return True
        return False

# FastAPI endpoints
@app.post("/v1/agents/{agent_id}/sandboxes")
async def create_agent_sandbox(
    agent_id: str,
    sandbox_request: dict,
    current_user: User = Depends(get_current_user)
):
    # Validate agent ownership
    agent = await get_agent_by_id(agent_id)
    if not agent or agent.org_id != current_user.org_id:
        raise HTTPException(404, "Agent not found")
    
    # Check if connected mode requires approval
    if sandbox_request["mode"] == "connected":
        approval_required = await check_approval_required(
            current_user.org_id,
            "sandbox_connected",
            {"agent_id": agent_id, "target_system": sandbox_request["target_system"]}
        )
        
        if approval_required:
            approval = await create_approval_request(
                org_id=current_user.org_id,
                subject_type="sandbox_connected",
                subject_id=agent_id,
                context=sandbox_request
            )
            return {"status": "pending_approval", "approval_id": approval.id}
    
    # Create sandbox
    sandbox_manager = SandboxManager()
    sandbox_id = f"{agent_id}-{uuid4().hex[:8]}"
    
    sandbox_info = await sandbox_manager.create_sandbox(
        sandbox_id=sandbox_id,
        target_system=sandbox_request["target_system"],
        mode=sandbox_request["mode"],
        config=sandbox_request.get("config", {})
    )
    
    # Store in database
    await store_sandbox(agent_id, sandbox_id, sandbox_info)
    
    return sandbox_info

@app.delete("/v1/agents/{agent_id}/sandboxes/{sandbox_id}")
async def stop_agent_sandbox(
    agent_id: str,
    sandbox_id: str,
    current_user: User = Depends(get_current_user)
):
    # Validate ownership
    sandbox = await get_sandbox_by_id(sandbox_id)
    if not sandbox or sandbox.agent.org_id != current_user.org_id:
        raise HTTPException(404, "Sandbox not found")
    
    sandbox_manager = SandboxManager()
    success = await sandbox_manager.stop_sandbox(sandbox_id)
    
    if success:
        await mark_sandbox_stopped(sandbox_id)
        return {"status": "stopped"}
    else:
        raise HTTPException(500, "Failed to stop sandbox")
```

---

## Milestone K — Billing Integration with Celery

### Async Stripe Webhook Processing

```python
# backend/app/tasks/billing_tasks.py
from celery import Celery
import stripe
from app.services.billing_service import update_subscription_status
from app.models.billing import BillingEvent

celery_app = Celery("collexa-billing")

@celery_app.task(bind=True, max_retries=3)
def process_stripe_webhook(self, webhook_data: dict, signature: str):
    """Process Stripe webhook events asynchronously"""
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload=webhook_data,
            sig_header=signature,
            secret=settings.STRIPE_WEBHOOK_SECRET
        )
        
        if event["type"] == "customer.subscription.created":
            await handle_subscription_created(event["data"]["object"])
        elif event["type"] == "customer.subscription.updated":
            await handle_subscription_updated(event["data"]["object"])
        elif event["type"] == "invoice.payment_succeeded":
            await handle_payment_succeeded(event["data"]["object"])
        elif event["type"] == "customer.subscription.deleted":
            await handle_subscription_canceled(event["data"]["object"])
        
        # Log billing event
        await BillingEvent.create(
            org_id=get_org_from_customer_id(event["data"]["object"]["customer"]),
            event_type=event["type"],
            amount_cents=event["data"]["object"].get("amount_total", 0),
            metadata=event["data"]["object"]
        )
        
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

# FastAPI webhook endpoint
@app.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    
    if not signature:
        raise HTTPException(400, "Missing stripe-signature header")
    
    # Queue for async processing
    background_tasks.add_task(
        process_stripe_webhook.delay,
        json.loads(payload),
        signature
    )
    
    return {"status": "received"}
```

---

## Next Steps

1. **Install Priority Dependencies**: Start with modelcontextprotocol/python, python-jose, and testcontainers-python
2. **Setup Development Environment**: Configure OPA, Redis, and Docker for local development
3. **Create Integration Tests**: Write Jest/pytest tests for each integration
4. **Add Configuration**: Extend settings.py with new service configurations
5. **Update Docker Compose**: Add new services (OPA, Redis, Vault) to development stack

See `docs/phase2-dependencies.md` for complete library recommendations and `docs/phase2-checklist.md` for milestone tracking.
