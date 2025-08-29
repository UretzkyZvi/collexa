"""
Tool registry for N.2 learning loop.

Keeps a minimal set of safe-by-default tools for mock/emulated modes. Designed
for future expansion (Playwright, Selenium, Docker, K8s, DBs, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .base import Tool
from .http_client import HttpClientTool
from .fs import FileSystemTool
from .graphql import GraphQLTool
from .ws import WebSocketTool
from .search import SearchTool


@dataclass
class ToolRegistry:
    tools: List[Tool] = field(default_factory=lambda: [
        HttpClientTool(), FileSystemTool(), GraphQLTool(), WebSocketTool(), SearchTool()
    ])

    def select(self, task: str) -> List[Tool]:
        return [t for t in self.tools if t.can_handle(task)]

