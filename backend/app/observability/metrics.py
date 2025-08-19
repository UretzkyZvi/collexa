"""
Basic metrics collection for API calls, invocations, and performance.
Uses in-memory storage for PoC; production would use Prometheus/DataDog.
"""
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from threading import Lock


@dataclass
class MetricPoint:
    timestamp: float
    value: float
    labels: Dict[str, str]


class MetricsCollector:
    """Thread-safe in-memory metrics collector for PoC."""
    
    def __init__(self, max_points: int = 10000):
        self._lock = Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self._gauges: Dict[str, float] = {}
        
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        key = self._make_key(name, labels or {})
        with self._lock:
            self._counters[key] += 1
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram value (for latency, etc.)."""
        key = self._make_key(name, labels or {})
        point = MetricPoint(timestamp=time.time(), value=value, labels=labels or {})
        with self._lock:
            self._histograms[key].append(point)
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge value."""
        key = self._make_key(name, labels or {})
        with self._lock:
            self._gauges[key] = value
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> int:
        """Get counter value aggregated over all series matching the label filter.

        If labels is None or empty, returns the sum over all series for the given name.
        If labels is provided, returns the sum over series whose labels include
        the provided labels as a subset (i.e., partial match / rollup by labels).
        """
        filter_labels = labels or {}
        with self._lock:
            items = list(self._counters.items())
        total = 0
        for key, value in items:
            metric_name, series_labels = self._parse_key(key)
            if metric_name != name:
                continue
            if self._labels_match(series_labels, filter_labels):
                total += value
        return total

    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict:
        """Get histogram statistics (count, p50, p95, p99) aggregated by label filter."""
        filter_labels = labels or {}
        with self._lock:
            items = list(self._histograms.items())
        # Aggregate all matching values
        values: List[float] = []
        for key, dq in items:
            metric_name, series_labels = self._parse_key(key)
            if metric_name != name:
                continue
            if self._labels_match(series_labels, filter_labels):
                values.extend([p.value for p in dq])
        if not values:
            return {"count": 0, "p50": 0, "p95": 0, "p99": 0, "avg": 0}
        values.sort()
        count = len(values)
        return {
            "count": count,
            "p50": self._percentile(values, 0.5),
            "p95": self._percentile(values, 0.95),
            "p99": self._percentile(values, 0.99),
            "avg": sum(values) / count,
        }

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current gauge value."""
        key = self._make_key(name, labels or {})
        with self._lock:
            return self._gauges.get(key, 0.0)
    
    def get_all_metrics(self) -> Dict:
        """Get all metrics for debugging/monitoring."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    key: self.get_histogram_stats("", {}) 
                    for key in self._histograms.keys()
                }
            }
    
    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """Create a unique key for metric with labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _parse_key(self, key: str) -> Tuple[str, Dict[str, str]]:
        """Parse a metric key back into name and labels dict."""
        if "{" not in key:
            return key, {}
        name, rest = key.split("{", 1)
        rest = rest.rstrip("}")
        labels: Dict[str, str] = {}
        if rest:
            for part in rest.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    labels[k] = v
        return name, labels

    def _labels_match(self, series_labels: Dict[str, str], filter_labels: Dict[str, str]) -> bool:
        """Return True if all filter_labels are present and equal in series_labels."""
        for k, v in filter_labels.items():
            if series_labels.get(k) != v:
                return False
        return True

    def _percentile(self, values: List[float], p: float) -> float:
        """Calculate percentile from sorted values."""
        if not values:
            return 0.0
        # Use nearest-rank style index
        index = int(p * (len(values) - 1))
        return values[index]


# Global metrics collector instance
metrics = MetricsCollector()


# Convenience functions
def increment_api_calls(endpoint: str, method: str, status_code: int, org_id: str):
    """Record API call metrics."""
    labels = {
        "endpoint": endpoint,
        "method": method,
        "status": str(status_code),
        "org_id": org_id
    }
    metrics.increment_counter("api_calls_total", labels)
    
    if status_code >= 400:
        metrics.increment_counter("api_errors_total", labels)


def record_request_duration(endpoint: str, method: str, duration_ms: float, org_id: str):
    """Record request duration metrics."""
    labels = {
        "endpoint": endpoint,
        "method": method,
        "org_id": org_id
    }
    metrics.record_histogram("request_duration_ms", duration_ms, labels)


def increment_agent_invocations(agent_id: str, org_id: str, capability: str, status: str):
    """Record agent invocation metrics."""
    labels = {
        "agent_id": agent_id,
        "org_id": org_id,
        "capability": capability,
        "status": status
    }
    metrics.increment_counter("agent_invocations_total", labels)


def record_agent_invocation_duration(agent_id: str, org_id: str, duration_ms: float):
    """Record agent invocation duration."""
    labels = {
        "agent_id": agent_id,
        "org_id": org_id
    }
    metrics.record_histogram("agent_invocation_duration_ms", duration_ms, labels)
