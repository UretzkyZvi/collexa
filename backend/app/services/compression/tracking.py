"""
SC.1-07: MLflow tracking adapter for compression metrics.

- Optional enablement via env var COMPRESSION_TRACKING=1
- Provides decorators/helpers to log compression sizes and ratios
- Safe if MLflow is unavailable; logs no-op
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Optional, Dict

try:
    import mlflow  # type: ignore
except Exception:  # pragma: no cover
    mlflow = None  # type: ignore


def tracking_enabled() -> bool:
    return os.getenv("COMPRESSION_TRACKING", "0") in ("1", "true", "True") and mlflow is not None


@contextmanager
def run(name: str, tags: Optional[Dict[str, str]] = None):
    if tracking_enabled():
        with mlflow.start_run(run_name=name):  # type: ignore[attr-defined]
            if tags:
                mlflow.set_tags(tags)  # type: ignore[attr-defined]
            yield
    else:
        yield


def log_metrics(metrics: Dict[str, float], step: Optional[int] = None, tags: Optional[Dict[str, str]] = None) -> None:
    if not tracking_enabled():
        return
    if tags:
        mlflow.set_tags(tags)  # type: ignore[attr-defined]
    mlflow.log_metrics(metrics, step=step)  # type: ignore[attr-defined]

