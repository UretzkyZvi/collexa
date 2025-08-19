import asyncio
import json
import os
import subprocess
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import models
from app.observability.logging import get_structured_logger

logger = get_structured_logger(__name__)


class SandboxService:
    """Service for managing agent sandbox environments."""
    
    def __init__(self, db: Session):
        self.db = db
        self.mock_containers: Dict[str, subprocess.Popen] = {}
    
    async def start_sandbox(self, sandbox_id: str) -> bool:
        """Start a sandbox environment."""
        sandbox = self.db.query(models.Sandbox).filter(models.Sandbox.id == sandbox_id).first()
        if not sandbox:
            raise ValueError(f"Sandbox {sandbox_id} not found")
        
        try:
            if sandbox.mode == "mock":
                await self._start_mock_server(sandbox)
            else:
                raise ValueError(f"Unsupported sandbox mode: {sandbox.mode}")
            
            # Update status
            sandbox.status = "running"
            sandbox.updated_at = func.now()
            self.db.commit()
            
            logger.info(
                "Sandbox started successfully",
                extra={
                    "sandbox_id": sandbox_id,
                    "mode": sandbox.mode,
                    "agent_id": sandbox.agent_id,
                    "event_type": "sandbox_started"
                }
            )
            return True
            
        except Exception as e:
            sandbox.status = "error"
            sandbox.updated_at = func.now()
            self.db.commit()
            
            logger.error(
                "Failed to start sandbox",
                extra={
                    "sandbox_id": sandbox_id,
                    "error": str(e),
                    "event_type": "sandbox_start_failed"
                }
            )
            raise
    
    async def stop_sandbox(self, sandbox_id: str) -> bool:
        """Stop a sandbox environment."""
        sandbox = self.db.query(models.Sandbox).filter(models.Sandbox.id == sandbox_id).first()
        if not sandbox:
            raise ValueError(f"Sandbox {sandbox_id} not found")
        
        try:
            if sandbox.mode == "mock":
                await self._stop_mock_server(sandbox_id)
            
            # Update status
            sandbox.status = "stopped"
            sandbox.updated_at = func.now()
            self.db.commit()
            
            logger.info(
                "Sandbox stopped successfully",
                extra={
                    "sandbox_id": sandbox_id,
                    "event_type": "sandbox_stopped"
                }
            )
            return True
            
        except Exception as e:
            logger.error(
                "Failed to stop sandbox",
                extra={
                    "sandbox_id": sandbox_id,
                    "error": str(e),
                    "event_type": "sandbox_stop_failed"
                }
            )
            raise
    
    async def reset_sandbox(self, sandbox_id: str) -> bool:
        """Reset sandbox state while preserving provenance."""
        sandbox = self.db.query(models.Sandbox).filter(models.Sandbox.id == sandbox_id).first()
        if not sandbox:
            raise ValueError(f"Sandbox {sandbox_id} not found")
        
        try:
            # Stop current instance
            await self.stop_sandbox(sandbox_id)
            
            # Clear runtime state but preserve runs for provenance
            # (In a real implementation, this would reset mock server state)
            
            # Restart
            await self.start_sandbox(sandbox_id)
            
            logger.info(
                "Sandbox reset successfully",
                extra={
                    "sandbox_id": sandbox_id,
                    "event_type": "sandbox_reset"
                }
            )
            return True
            
        except Exception as e:
            logger.error(
                "Failed to reset sandbox",
                extra={
                    "sandbox_id": sandbox_id,
                    "error": str(e),
                    "event_type": "sandbox_reset_failed"
                }
            )
            raise
    
    async def create_sandbox_run(
        self, 
        sandbox_id: str, 
        phase: str, 
        task_name: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new sandbox run."""
        run_id = str(uuid.uuid4())
        
        run = models.SandboxRun(
            id=run_id,
            sandbox_id=sandbox_id,
            phase=phase,
            task_name=task_name,
            status="running",
            input_json=input_data
        )
        
        self.db.add(run)
        self.db.commit()
        
        logger.info(
            "Sandbox run created",
            extra={
                "run_id": run_id,
                "sandbox_id": sandbox_id,
                "phase": phase,
                "task_name": task_name,
                "event_type": "sandbox_run_created"
            }
        )
        
        return run_id
    
    async def complete_sandbox_run(
        self,
        run_id: str,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        error_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Complete a sandbox run with results."""
        run = self.db.query(models.SandboxRun).filter(models.SandboxRun.id == run_id).first()
        if not run:
            raise ValueError(f"Sandbox run {run_id} not found")
        
        run.status = status
        run.output_json = output_data
        run.error_json = error_data
        run.finished_at = func.now()
        
        self.db.commit()
        
        logger.info(
            "Sandbox run completed",
            extra={
                "run_id": run_id,
                "status": status,
                "event_type": "sandbox_run_completed"
            }
        )
        
        return True
    
    async def _start_mock_server(self, sandbox: models.Sandbox) -> None:
        """Start Prism mock server for the sandbox."""
        # In N.1, we'll use a simple mock approach
        # In a full implementation, this would start a Prism container
        
        # Create mock server configuration
        mock_config = {
            "sandbox_id": sandbox.id,
            "agent_id": sandbox.agent_id,
            "target_system": sandbox.target_system,
            "endpoints": self._get_default_mock_endpoints(sandbox.target_system)
        }
        
        # For N.1, we'll simulate the mock server without actually starting containers
        # In production, this would use testcontainers-python to start Prism
        
        logger.info(
            "Mock server configuration created",
            extra={
                "sandbox_id": sandbox.id,
                "config": mock_config,
                "event_type": "mock_server_configured"
            }
        )
    
    async def _stop_mock_server(self, sandbox_id: str) -> None:
        """Stop mock server for the sandbox."""
        # In N.1, cleanup mock server resources
        if sandbox_id in self.mock_containers:
            container = self.mock_containers[sandbox_id]
            container.terminate()
            del self.mock_containers[sandbox_id]
        
        logger.info(
            "Mock server stopped",
            extra={
                "sandbox_id": sandbox_id,
                "event_type": "mock_server_stopped"
            }
        )
    
    def _get_default_mock_endpoints(self, target_system: Optional[str]) -> Dict[str, Any]:
        """Get default mock endpoints for a target system."""
        if target_system == "figma":
            return {
                "base_url": "https://api.figma.com/v1",
                "endpoints": {
                    "/files/{file_key}": {"method": "GET", "response": {"name": "Mock Design File"}},
                    "/files/{file_key}/nodes": {"method": "GET", "response": {"nodes": {}}},
                }
            }
        elif target_system == "slack":
            return {
                "base_url": "https://slack.com/api",
                "endpoints": {
                    "/chat.postMessage": {"method": "POST", "response": {"ok": True, "ts": "1234567890.123456"}},
                    "/users.list": {"method": "GET", "response": {"ok": True, "members": []}},
                }
            }
        else:
            # Generic REST API mock
            return {
                "base_url": "https://api.example.com",
                "endpoints": {
                    "/status": {"method": "GET", "response": {"status": "ok"}},
                    "/data": {"method": "GET", "response": {"data": []}},
                }
            }
    
    async def get_learning_plan(self, agent_id: str) -> Optional[models.LearningPlan]:
        """Get or create a learning plan for an agent."""
        plan = (
            self.db.query(models.LearningPlan)
            .filter(models.LearningPlan.agent_id == agent_id)
            .first()
        )
        
        if not plan:
            # Create default learning plan
            plan = models.LearningPlan(
                id=str(uuid.uuid4()),
                agent_id=agent_id,
                objectives_json={
                    "primary": "Learn to interact with target system APIs",
                    "secondary": ["Handle authentication", "Process responses", "Error handling"]
                },
                curriculum_json={
                    "phases": [
                        {"name": "Discovery", "tasks": ["explore_endpoints", "test_authentication"]},
                        {"name": "Basic Operations", "tasks": ["create_resource", "read_resource", "update_resource"]},
                        {"name": "Advanced Features", "tasks": ["batch_operations", "error_recovery"]}
                    ]
                },
                status="draft"
            )
            
            self.db.add(plan)
            self.db.commit()
            
            logger.info(
                "Learning plan created",
                extra={
                    "agent_id": agent_id,
                    "plan_id": plan.id,
                    "event_type": "learning_plan_created"
                }
            )
        
        return plan
