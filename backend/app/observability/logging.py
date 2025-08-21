"""
Structured logging utilities with request_id, org_id, agent_id context.
"""

import logging
import json
from typing import Optional
from contextvars import ContextVar

# Context variables for request-scoped data
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
org_id_ctx: ContextVar[Optional[str]] = ContextVar("org_id", default=None)
agent_id_ctx: ContextVar[Optional[str]] = ContextVar("agent_id", default=None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter that includes context variables."""

    def format(self, record: logging.LogRecord) -> str:
        # Base log data
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context if available
        if request_id := request_id_ctx.get():
            log_data["request_id"] = request_id
        if org_id := org_id_ctx.get():
            log_data["org_id"] = org_id
        if agent_id := agent_id_ctx.get():
            log_data["agent_id"] = agent_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            ):
                log_data[key] = value

        return json.dumps(log_data, default=str)


def get_structured_logger(name: str) -> logging.Logger:
    """Get a logger with structured formatting."""
    logger = logging.getLogger(name)

    # Only add handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


def set_request_context(
    request_id: str, org_id: Optional[str] = None, agent_id: Optional[str] = None
):
    """Set context variables for the current request."""
    request_id_ctx.set(request_id)
    if org_id:
        org_id_ctx.set(org_id)
    if agent_id:
        agent_id_ctx.set(agent_id)


def log_api_call(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **extra,
):
    """Log an API call with structured data."""
    logger.info(
        f"{method} {path} -> {status_code}",
        extra={
            "event_type": "api_call",
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            **extra,
        },
    )


def log_agent_invocation(
    logger: logging.Logger,
    agent_id: str,
    capability: str,
    status: str,
    duration_ms: float,
    **extra,
):
    """Log an agent invocation with structured data."""
    logger.info(
        f"Agent {agent_id} invoked with {capability} -> {status}",
        extra={
            "event_type": "agent_invocation",
            "agent_id": agent_id,
            "capability": capability,
            "status": status,
            "duration_ms": duration_ms,
            **extra,
        },
    )


# Default structured logger
logger = get_structured_logger("collexa")
