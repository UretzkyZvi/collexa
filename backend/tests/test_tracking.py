import os
from unittest.mock import patch

from app.services.compression.tracking import tracking_enabled, run, log_metrics


def test_tracking_disabled_by_default(monkeypatch):
    monkeypatch.delenv("COMPRESSION_TRACKING", raising=False)
    assert tracking_enabled() is False


def test_tracking_noop_without_mlflow(monkeypatch):
    monkeypatch.setenv("COMPRESSION_TRACKING", "1")
    with patch("app.services.compression.tracking.mlflow", None):
        assert tracking_enabled() is False
        # Should not raise
        with run("test"):
            log_metrics({"a": 1.0})


def test_tracking_with_mlflow_mock(monkeypatch):
    class DummyML:
        def __init__(self):
            self.started = False
            self.tags = {}
            self.metrics = []
        def start_run(self, run_name=None):
            self.started = True
            class Ctx:
                def __enter__(_):
                    return None
                def __exit__(_, exc_type, exc, tb):
                    return False
            return Ctx()
        def set_tags(self, tags):
            self.tags.update(tags)
        def log_metrics(self, m, step=None):
            self.metrics.append(m)

    dummy = DummyML()
    monkeypatch.setenv("COMPRESSION_TRACKING", "true")
    with patch("app.services.compression.tracking.mlflow", dummy):
        assert tracking_enabled() is True
        with run("r1", tags={"k": "v"}):
            log_metrics({"ratio": 2.0}, tags={"phase": "unit"})
        assert dummy.started is True
        assert dummy.tags.get("k") == "v"
        assert any("ratio" in m for m in dummy.metrics)

