"""
OpenTelemetry tracing stub for PoC.
In production, this would integrate with Jaeger, Zipkin, or cloud tracing services.
"""
import time
from typing import Dict, Any, Optional
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class Span:
    """Simple span implementation for tracing."""
    name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    parent_span_id: Optional[str] = None
    span_id: str = field(default_factory=lambda: f"span_{int(time.time() * 1000000)}")
    
    def set_attribute(self, key: str, value: Any):
        """Set a span attribute."""
        self.attributes[key] = value
    
    def finish(self):
        """Finish the span."""
        self.end_time = time.time()
    
    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000


# Context variable for current span
current_span_ctx: ContextVar[Optional[Span]] = ContextVar('current_span', default=None)


class Tracer:
    """Simple tracer implementation."""
    
    def __init__(self, name: str):
        self.name = name
        self.spans: list[Span] = []
    
    def start_span(self, name: str, parent: Optional[Span] = None) -> Span:
        """Start a new span."""
        parent_id = parent.span_id if parent else current_span_ctx.get()
        parent_id = parent_id.span_id if hasattr(parent_id, 'span_id') else parent_id
        
        span = Span(
            name=name,
            parent_span_id=parent_id
        )
        
        self.spans.append(span)
        current_span_ctx.set(span)
        return span
    
    def get_current_span(self) -> Optional[Span]:
        """Get the current active span."""
        return current_span_ctx.get()
    
    def get_spans(self) -> list[Span]:
        """Get all spans for debugging."""
        return self.spans.copy()


# Global tracer instance
tracer = Tracer("collexa")


def trace_function(name: str):
    """Decorator to trace function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            span = tracer.start_span(f"{func.__module__}.{func.__name__}")
            span.set_attribute("function.name", func.__name__)
            span.set_attribute("function.module", func.__module__)
            
            try:
                result = func(*args, **kwargs)
                span.set_attribute("function.result", "success")
                return result
            except Exception as e:
                span.set_attribute("function.result", "error")
                span.set_attribute("function.error", str(e))
                raise
            finally:
                span.finish()
        
        async def async_wrapper(*args, **kwargs):
            span = tracer.start_span(f"{func.__module__}.{func.__name__}")
            span.set_attribute("function.name", func.__name__)
            span.set_attribute("function.module", func.__module__)
            
            try:
                result = await func(*args, **kwargs)
                span.set_attribute("function.result", "success")
                return result
            except Exception as e:
                span.set_attribute("function.result", "error")
                span.set_attribute("function.error", str(e))
                raise
            finally:
                span.finish()
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator


def start_span(name: str, **attributes) -> Span:
    """Start a new span with attributes."""
    span = tracer.start_span(name)
    for key, value in attributes.items():
        span.set_attribute(key, value)
    return span


def get_current_span() -> Optional[Span]:
    """Get the current active span."""
    return tracer.get_current_span()


def add_span_attribute(key: str, value: Any):
    """Add attribute to current span if active."""
    span = get_current_span()
    if span:
        span.set_attribute(key, value)
