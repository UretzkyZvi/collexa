"""
Dynamic Sandbox Orchestrator

Manages on-demand creation and lifecycle of sandbox environments with
custom mock services tailored to each agent's requirements.
"""

import asyncio
import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

import docker
import yaml
from jinja2 import Template
from pydantic import BaseModel


class ServiceConfig(BaseModel):
    """Configuration for a mock service within a sandbox."""
    service_type: str  # figma, slack, github, etc.
    custom_responses: Dict[str, Any] = {}
    custom_endpoints: List[Dict[str, Any]] = []
    workspace_config: Dict[str, Any] = {}


class SandboxRequest(BaseModel):
    """Request to create a new dynamic sandbox."""
    required_services: List[str]
    custom_configs: Dict[str, ServiceConfig] = {}
    ttl_minutes: int = 60
    resource_limits: Dict[str, Any] = {}


class SandboxService(BaseModel):
    """Information about a running service within a sandbox."""
    container_id: str
    port: int
    url: str
    status: str  # starting, running, stopping, stopped
    spec_path: str
    endpoints: List[str] = []


class SandboxInfo(BaseModel):
    """Complete information about a sandbox and its services."""
    sandbox_id: str
    agent_id: str
    services: Dict[str, SandboxService]
    status: str  # creating, running, stopping, stopped
    created_at: datetime
    expires_at: datetime
    last_accessed: datetime
    proxy_url: str


class SandboxOrchestrator:
    """
    Orchestrates dynamic sandbox environments with on-demand mock services.
    """
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.active_sandboxes: Dict[str, SandboxInfo] = {}
        self.port_allocator = PortAllocator(start_port=45000)
        self.template_loader = TemplateLoader()
        
    async def create_sandbox(
        self, 
        agent_id: str, 
        request: SandboxRequest
    ) -> SandboxInfo:
        """Create a new dynamic sandbox with requested services."""
        
        sandbox_id = f"sb_{uuid4().hex[:8]}"
        expires_at = datetime.utcnow() + timedelta(minutes=request.ttl_minutes)
        
        # Initialize sandbox info
        sandbox_info = SandboxInfo(
            sandbox_id=sandbox_id,
            agent_id=agent_id,
            services={},
            status="creating",
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            last_accessed=datetime.utcnow(),
            proxy_url=f"http://localhost:4000/sandbox/{sandbox_id}"
        )
        
        self.active_sandboxes[sandbox_id] = sandbox_info
        
        try:
            # Create services concurrently
            service_tasks = []
            for service_type in request.required_services:
                custom_config = request.custom_configs.get(service_type, ServiceConfig(service_type=service_type))
                task = self._create_service(sandbox_id, service_type, custom_config)
                service_tasks.append(task)
            
            # Wait for all services to start
            services = await asyncio.gather(*service_tasks)
            
            # Update sandbox info with created services
            for service in services:
                sandbox_info.services[service.service_type] = service
            
            sandbox_info.status = "running"
            
        except Exception as e:
            sandbox_info.status = "failed"
            # Cleanup any partially created services
            await self._cleanup_sandbox(sandbox_id)
            raise Exception(f"Failed to create sandbox: {str(e)}")
        
        return sandbox_info
    
    async def _create_service(
        self, 
        sandbox_id: str, 
        service_type: str, 
        config: ServiceConfig
    ) -> SandboxService:
        """Create a single mock service container."""
        
        # Allocate port for this service
        port = self.port_allocator.allocate()
        
        # Generate custom OpenAPI spec
        spec_content = await self.template_loader.generate_spec(
            service_type, 
            config.custom_responses,
            config.custom_endpoints,
            config.workspace_config
        )
        
        # Write spec to temporary file
        spec_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix=f'_{sandbox_id}_{service_type}.yaml',
            delete=False
        )
        spec_file.write(spec_content)
        spec_file.close()
        
        # Create container with custom spec
        container_name = f"prism_{service_type}_{sandbox_id}"
        
        try:
            container = self.docker_client.containers.run(
                image="stoplight/prism:4",
                command=f"mock -h 0.0.0.0 -p 4010 /specs/{service_type}.yaml",
                ports={'4010/tcp': port},
                volumes={
                    spec_file.name: {
                        'bind': f'/specs/{service_type}.yaml',
                        'mode': 'ro'
                    }
                },
                environment={
                    'PRISM_LOG_LEVEL': 'info'
                },
                name=container_name,
                detach=True,
                remove=True,  # Auto-remove when stopped
                labels={
                    'collexa.sandbox_id': sandbox_id,
                    'collexa.service_type': service_type,
                    'collexa.created_at': datetime.utcnow().isoformat()
                }
            )
            
            # Wait for container to be ready
            await self._wait_for_service_ready(f"http://localhost:{port}")
            
            # Get available endpoints from spec
            endpoints = self.template_loader.get_endpoints(service_type)
            
            return SandboxService(
                container_id=container.id,
                port=port,
                url=f"http://localhost:{port}",
                status="running",
                spec_path=spec_file.name,
                endpoints=endpoints
            )
            
        except Exception as e:
            # Cleanup on failure
            self.port_allocator.release(port)
            Path(spec_file.name).unlink(missing_ok=True)
            raise Exception(f"Failed to create {service_type} service: {str(e)}")
    
    async def _wait_for_service_ready(self, url: str, timeout: int = 30):
        """Wait for a service to be ready to accept requests."""
        import aiohttp
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url}/", timeout=5) as response:
                        # Prism returns 404 for root, which means it's ready
                        if response.status in [200, 404]:
                            return
            except:
                pass
            await asyncio.sleep(1)
        
        raise Exception(f"Service at {url} did not become ready within {timeout}s")
    
    async def get_sandbox(self, sandbox_id: str) -> Optional[SandboxInfo]:
        """Get information about a sandbox."""
        sandbox = self.active_sandboxes.get(sandbox_id)
        if sandbox:
            sandbox.last_accessed = datetime.utcnow()
        return sandbox
    
    async def update_sandbox(
        self, 
        sandbox_id: str, 
        add_services: List[str] = None,
        update_configs: Dict[str, ServiceConfig] = None
    ) -> SandboxInfo:
        """Update an existing sandbox by adding services or updating configs."""
        
        sandbox = self.active_sandboxes.get(sandbox_id)
        if not sandbox:
            raise Exception(f"Sandbox {sandbox_id} not found")
        
        # Add new services
        if add_services:
            for service_type in add_services:
                if service_type not in sandbox.services:
                    config = update_configs.get(service_type, ServiceConfig(service_type=service_type))
                    service = await self._create_service(sandbox_id, service_type, config)
                    sandbox.services[service_type] = service
        
        # Update existing service configs (requires recreation)
        if update_configs:
            for service_type, config in update_configs.items():
                if service_type in sandbox.services:
                    # Stop old service
                    await self._stop_service(sandbox.services[service_type])
                    # Create new service with updated config
                    service = await self._create_service(sandbox_id, service_type, config)
                    sandbox.services[service_type] = service
        
        sandbox.last_accessed = datetime.utcnow()
        return sandbox
    
    async def delete_sandbox(self, sandbox_id: str) -> bool:
        """Delete a sandbox and cleanup all its resources."""
        if sandbox_id not in self.active_sandboxes:
            return False
        
        await self._cleanup_sandbox(sandbox_id)
        del self.active_sandboxes[sandbox_id]
        return True
    
    async def _cleanup_sandbox(self, sandbox_id: str):
        """Cleanup all resources for a sandbox."""
        sandbox = self.active_sandboxes.get(sandbox_id)
        if not sandbox:
            return
        
        # Stop all services
        cleanup_tasks = []
        for service in sandbox.services.values():
            cleanup_tasks.append(self._stop_service(service))
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    async def _stop_service(self, service: SandboxService):
        """Stop a single service and cleanup its resources."""
        try:
            # Stop container
            container = self.docker_client.containers.get(service.container_id)
            container.stop(timeout=10)
            
            # Release port
            self.port_allocator.release(service.port)
            
            # Remove spec file
            Path(service.spec_path).unlink(missing_ok=True)
            
        except Exception as e:
            print(f"Error stopping service {service.container_id}: {e}")
    
    async def cleanup_expired_sandboxes(self):
        """Cleanup sandboxes that have exceeded their TTL."""
        now = datetime.utcnow()
        expired_sandboxes = [
            sandbox_id for sandbox_id, sandbox in self.active_sandboxes.items()
            if sandbox.expires_at < now
        ]
        
        for sandbox_id in expired_sandboxes:
            await self.delete_sandbox(sandbox_id)
    
    def get_active_sandboxes(self) -> Dict[str, SandboxInfo]:
        """Get all currently active sandboxes."""
        return self.active_sandboxes.copy()


class PortAllocator:
    """Manages dynamic port allocation for sandbox services."""
    
    def __init__(self, start_port: int = 45000):
        self.start_port = start_port
        self.allocated_ports = set()
        self.next_port = start_port
    
    def allocate(self) -> int:
        """Allocate the next available port."""
        while self.next_port in self.allocated_ports:
            self.next_port += 1
        
        port = self.next_port
        self.allocated_ports.add(port)
        self.next_port += 1
        return port
    
    def release(self, port: int):
        """Release a port back to the pool."""
        self.allocated_ports.discard(port)


class TemplateLoader:
    """Loads and processes OpenAPI spec templates."""
    
    def __init__(self):
        self.templates_dir = Path("app/templates/sandbox")
        self.templates_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_spec(
        self, 
        service_type: str, 
        custom_responses: Dict[str, Any],
        custom_endpoints: List[Dict[str, Any]],
        workspace_config: Dict[str, Any]
    ) -> str:
        """Generate a custom OpenAPI spec from template."""
        
        template_path = self.templates_dir / f"{service_type}.yaml.j2"
        if not template_path.exists():
            raise Exception(f"No template found for {service_type} at {template_path}")
        
        template = Template(template_path.read_text())
        
        return template.render(
            custom_responses=custom_responses,
            custom_endpoints=custom_endpoints,
            workspace_config=workspace_config,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def get_endpoints(self, service_type: str) -> List[str]:
        """Get list of available endpoints for a service type."""
        # This would parse the OpenAPI spec and extract endpoint paths
        # For now, return static lists
        endpoint_map = {
            "figma": ["/me", "/files/{key}", "/files/{key}/nodes", "/files/{key}/comments"],
            "slack": ["/auth.test", "/chat.postMessage", "/channels.list", "/users.list"],
            "github": ["/user", "/repos", "/repos/{owner}/{repo}", "/repos/{owner}/{repo}/issues"],
            "generic": ["/status", "/items", "/items/{id}", "/categories"]
        }
        return endpoint_map.get(service_type, [])


# Global orchestrator instance
orchestrator = SandboxOrchestrator()
