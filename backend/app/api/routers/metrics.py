from fastapi import APIRouter, Depends
from app.api.deps import require_auth
from app.observability.metrics import metrics

router = APIRouter()


@router.get("/metrics")
async def get_metrics(auth=Depends(require_auth)):
    """Get basic metrics for monitoring and debugging."""
    org_id = auth.get("org_id")
    
    # Get org-specific metrics
    api_calls = metrics.get_counter("api_calls_total", {"org_id": org_id})
    api_errors = metrics.get_counter("api_errors_total", {"org_id": org_id})
    
    # Get request duration stats
    duration_stats = metrics.get_histogram_stats("request_duration_ms", {"org_id": org_id})
    
    # Get agent invocation stats
    invocation_stats = metrics.get_histogram_stats("agent_invocation_duration_ms", {"org_id": org_id})
    invocation_count = metrics.get_counter("agent_invocations_total", {"org_id": org_id})
    
    return {
        "org_id": org_id,
        "api_calls": {
            "total": api_calls,
            "errors": api_errors,
            "success_rate": (api_calls - api_errors) / api_calls if api_calls > 0 else 1.0,
        },
        "request_duration_ms": duration_stats,
        "agent_invocations": {
            "total": invocation_count,
            "duration_ms": invocation_stats,
        },
    }


@router.get("/metrics/all")
async def get_all_metrics(auth=Depends(require_auth)):
    """Get all metrics (for debugging/admin)."""
    # Only allow for specific users or admin role in production
    return metrics.get_all_metrics()
