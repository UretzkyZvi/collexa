"""
Budget management API endpoints.

This module provides REST API endpoints for managing budgets,
viewing usage, and configuring budget alerts.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.db.session import get_db
from app.db import models
from app.services.budget_service import BudgetService, BudgetPeriod, EnforcementMode
from app.services.usage_orchestrator import UsageOrchestrator
from app.services.usage.cost_calculation_service import CostCalculationService
from app.api.deps import get_current_org_id
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateBudgetRequest(BaseModel):
    """Request model for creating a budget"""
    agent_id: Optional[str] = Field(None, description="Agent ID (null for org-level budget)")
    period: str = Field(..., description="Budget period: daily, weekly, monthly")
    limit_cents: int = Field(..., gt=0, description="Budget limit in cents")
    enforcement_mode: str = Field("soft", description="Enforcement mode: soft or hard")
    alerts_config: Optional[Dict[str, Any]] = Field(None, description="Alert configuration")


class UpdateBudgetRequest(BaseModel):
    """Request model for updating a budget"""
    limit_cents: Optional[int] = Field(None, gt=0, description="New budget limit in cents")
    enforcement_mode: Optional[str] = Field(None, description="New enforcement mode")
    alerts_config: Optional[Dict[str, Any]] = Field(None, description="New alert configuration")


class BudgetResponse(BaseModel):
    """Response model for budget information"""
    id: str
    org_id: str
    agent_id: Optional[str]
    period: str
    limit_cents: int
    current_usage_cents: int
    utilization_percent: float
    period_start: str
    period_end: str
    enforcement_mode: str
    status: str
    alerts_config: Dict[str, Any]
    created_at: str
    updated_at: Optional[str]


class UsageSummaryResponse(BaseModel):
    """Response model for usage summary"""
    total_cost_cents: int
    total_cost_dollars: float
    usage_by_type: Dict[str, Dict[str, Any]]
    record_count: int
    period_start: Optional[str]
    period_end: Optional[str]


@router.post("/budgets", response_model=BudgetResponse)
async def create_budget(
    request: CreateBudgetRequest,
    org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db)
):
    """Create a new budget for the organization or a specific agent"""
    try:
        # Validate period
        try:
            period = BudgetPeriod(request.period)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid period: {request.period}")
        
        # Validate enforcement mode
        try:
            enforcement_mode = EnforcementMode(request.enforcement_mode)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid enforcement mode: {request.enforcement_mode}")
        
        budget_service = BudgetService(db)
        budget = budget_service.create_budget(
            org_id=org_id,
            period=period,
            limit_cents=request.limit_cents,
            agent_id=request.agent_id,
            enforcement_mode=enforcement_mode,
            alerts_config=request.alerts_config
        )
        
        return _budget_to_response(budget)
        
    except Exception as e:
        logger.error(f"Error creating budget: {e}")
        raise HTTPException(status_code=500, detail="Failed to create budget")


@router.get("/budgets", response_model=List[BudgetResponse])
async def list_budgets(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db)
):
    """List all budgets for the organization"""
    try:
        budget_service = BudgetService(db)
        budgets = budget_service.get_budgets_for_org(org_id, agent_id)
        
        return [_budget_to_response(budget) for budget in budgets]
        
    except Exception as e:
        logger.error(f"Error listing budgets: {e}")
        raise HTTPException(status_code=500, detail="Failed to list budgets")


@router.get("/budgets/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: str,
    org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db)
):
    """Get a specific budget by ID"""
    try:
        budget_service = BudgetService(db)
        budget = budget_service.get_budget(budget_id)
        
        if not budget or budget.org_id != org_id:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        return _budget_to_response(budget)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting budget {budget_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get budget")


@router.put("/budgets/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    request: UpdateBudgetRequest,
    org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db)
):
    """Update a budget"""
    try:
        budget_service = BudgetService(db)
        
        # Verify budget exists and belongs to org
        existing_budget = budget_service.get_budget(budget_id)
        if not existing_budget or existing_budget.org_id != org_id:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        # Validate enforcement mode if provided
        enforcement_mode = None
        if request.enforcement_mode:
            try:
                enforcement_mode = EnforcementMode(request.enforcement_mode)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid enforcement mode: {request.enforcement_mode}")
        
        budget = budget_service.update_budget(
            budget_id=budget_id,
            limit_cents=request.limit_cents,
            enforcement_mode=enforcement_mode,
            alerts_config=request.alerts_config
        )
        
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        return _budget_to_response(budget)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating budget {budget_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update budget")


@router.get("/usage/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    period_start: Optional[str] = Query(None, description="Period start (ISO format)"),
    period_end: Optional[str] = Query(None, description="Period end (ISO format)"),
    org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db)
):
    """Get usage summary for the organization or a specific agent"""
    try:
        # Parse dates if provided
        start_date = None
        end_date = None
        
        if period_start:
            try:
                start_date = datetime.fromisoformat(period_start.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid period_start format")
        
        if period_end:
            try:
                end_date = datetime.fromisoformat(period_end.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid period_end format")
        
        usage_orchestrator = UsageOrchestrator(db)
        summary = usage_orchestrator.get_usage_summary(
            org_id=org_id,
            agent_id=agent_id,
            period_start=start_date,
            period_end=end_date
        )
        
        return UsageSummaryResponse(**summary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usage summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage summary")


@router.get("/usage/current-month", response_model=UsageSummaryResponse)
async def get_current_month_usage(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db)
):
    """Get usage summary for the current month"""
    try:
        usage_orchestrator = UsageOrchestrator(db)
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        summary = usage_orchestrator.get_usage_summary(
            org_id=org_id,
            agent_id=agent_id,
            period_start=start_of_month,
            period_end=now
        )
        
        return UsageSummaryResponse(**summary)
        
    except Exception as e:
        logger.error(f"Error getting current month usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get current month usage")


@router.get("/usage/report")
async def generate_usage_report(
    start_date: str = Query(..., description="Report start date (ISO format)"),
    end_date: str = Query(..., description="Report end date (ISO format)"),
    org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db)
):
    """Generate comprehensive usage report"""
    try:
        # Parse dates
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
        
        usage_orchestrator = UsageOrchestrator(db)

        # Generate comprehensive report
        summary = usage_orchestrator.get_usage_summary(org_id, None, start, end)
        budget_status = usage_orchestrator.get_budget_status(org_id)

        # Get usage by agent
        agents_query = db.query(models.Agent).filter(models.Agent.org_id == org_id)
        agents = agents_query.all()

        agent_usage = {}
        for agent in agents:
            agent_summary = usage_orchestrator.get_usage_summary(
                org_id=org_id,
                agent_id=agent.id,
                period_start=start,
                period_end=end
            )
            if agent_summary["record_count"] > 0:
                agent_usage[agent.id] = {
                    "agent_name": agent.display_name,
                    **agent_summary
                }

        report = {
            "org_id": org_id,
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            "summary": summary,
            "agent_usage": agent_usage,
            "budget_status": budget_status,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating usage report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate usage report")


@router.get("/pricing")
async def get_pricing_rates(db: Session = Depends(get_db)):
    """Get current pricing rates"""
    try:
        cost_calculator = CostCalculationService()
        rates = cost_calculator.get_pricing_rates()
        
        descriptions = cost_calculator.get_usage_descriptions()

        return {
            "rates_cents_per_unit": rates,
            "descriptions": descriptions
        }
        
    except Exception as e:
        logger.error(f"Error getting pricing rates: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pricing rates")


# Helper functions

def _budget_to_response(budget) -> BudgetResponse:
    """Convert budget model to response"""
    utilization_percent = 0
    if budget.limit_cents > 0:
        utilization_percent = (budget.current_usage_cents / budget.limit_cents) * 100
    
    return BudgetResponse(
        id=budget.id,
        org_id=budget.org_id,
        agent_id=budget.agent_id,
        period=budget.period,
        limit_cents=budget.limit_cents,
        current_usage_cents=budget.current_usage_cents,
        utilization_percent=round(utilization_percent, 2),
        period_start=budget.period_start.isoformat(),
        period_end=budget.period_end.isoformat(),
        enforcement_mode=budget.enforcement_mode,
        status=budget.status,
        alerts_config=budget.alerts_json or {},
        created_at=budget.created_at.isoformat(),
        updated_at=budget.updated_at.isoformat() if budget.updated_at else None
    )
