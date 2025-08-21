"""
Legacy-compatible SandboxService used by tests.

Provides minimal behavior and method names referenced by tests to avoid breaking
existing test-suite while the new domain/orchestrator modules exist.
"""

from __future__ import annotations

from typing import Dict, Any


class SandboxService:
    """Thin compatibility layer.

    Methods are intentionally simple; tests patch these methods so they should be
    synchronous and side-effect free by default.
    """

    def _get_default_mock_endpoints(self, target_system: str) -> Dict[str, Any]:
        """Return default mock endpoints/config for a given target system.

        This mirrors the structure tests expect to patch/inspect.
        """
        # Minimal static defaults; tests usually patch this method.
        if target_system == "figma":
            return {
                "base_url": "http://localhost:4000/sandbox/{sandbox_id}/figma",
                "prism_url": "http://localhost:4010",
                "spec_file": "sandbox-specs/figma/figma-api.yaml",
                "endpoints": {
                    "/me": {"method": "GET", "description": "Get current user info"},
                    "/files/{file_key}": {
                        "method": "GET",
                        "description": "Get file information",
                    },
                },
            }
        # Generic fallback
        return {
            "base_url": f"http://localhost:4000/sandbox/{{sandbox_id}}/{target_system}",
            "prism_url": "http://localhost:4010",
            "spec_file": f"sandbox-specs/{target_system}/openapi.yaml",
            "endpoints": {
                "/status": {"method": "GET", "description": "Service status"}
            },
        }

    # The following are sync functions by design so tests can patch without AsyncMock
    def start_sandbox(self, sandbox_id: str | None = None) -> None:  # noqa: D401
        """Start a sandbox (no-op for tests)."""
        return None

    def reset_sandbox(self, sandbox_id: str) -> None:  # noqa: D401
        """Reset a sandbox (no-op for tests)."""
        return None

    def stop_sandbox(self, sandbox_id: str) -> None:  # noqa: D401
        """Stop a sandbox (no-op for tests)."""
        return None
