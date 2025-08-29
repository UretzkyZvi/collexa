"""
SC.1-05: Hierarchical Context Manager

Assembles compressed context across layers (GLOBAL, DOMAIN, SESSION, LOCAL)
within configurable byte budgets. Uses BasicCompressionEngine and accepts
items encoded as LSL/ADL/OPL/text/json. Selection is by layer precedence and
priority, honoring per-layer and total budgets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .basic_engine import BasicCompressionEngine, CompressionResult
from .lsl import CompressedLearningSession
from .adl import CompressedAgentBrief
from .opl import CompressedOptimizationTrace
from .tracking import log_metrics, run as tracking_run


class ContextLayer(Enum):
    GLOBAL = 1
    DOMAIN = 2
    SESSION = 3
    LOCAL = 4


@dataclass
class ContextItem:
    key: str
    layer: ContextLayer
    priority: int
    format: str  # 'lsl' | 'adl' | 'opl' | 'text' | 'json'
    payload: Any
    _compressed: Optional[CompressionResult] = field(default=None, init=False, repr=False)


class HierarchicalContextManager:
    def __init__(
        self,
        engine: Optional[BasicCompressionEngine] = None,
        total_budget_bytes: int = 20_000,
        per_layer_budget: Optional[Dict[ContextLayer, int]] = None,
    ) -> None:
        self.engine = engine or BasicCompressionEngine()
        # Default split: 40/30/20/10
        default = {
            ContextLayer.GLOBAL: int(total_budget_bytes * 0.40),
            ContextLayer.DOMAIN: int(total_budget_bytes * 0.30),
            ContextLayer.SESSION: int(total_budget_bytes * 0.20),
            ContextLayer.LOCAL: int(total_budget_bytes * 0.10),
        }
        if per_layer_budget:
            default.update(per_layer_budget)
        self.per_layer_budget = default
        self.total_budget = total_budget_bytes
        self._items: List[ContextItem] = []
        self._seq = 0  # insertion order breaker for stable sorts

    def add_item(self, key: str, layer: ContextLayer, payload: Any, fmt: str, priority: int = 0) -> None:
        self._items.append(ContextItem(key=key, layer=layer, priority=priority, format=fmt, payload=payload))

    def preselect_with_retriever(self, query_text: str, retriever, top_k: int = 50, filter_fn=None) -> None:
        """Use a VectorRetriever-like object to prune items before assembly.

        The retriever must support add_item(key, text, metadata) and query(text, top_k, filter_fn).
        We'll encode payloads to text and keep only items whose keys are returned by the retriever.
        """
        # Build index from current items
        for it in self._items:
            text = self._encode_payload(it)
            # Ensure text for vectorization
            if not isinstance(text, str):
                try:
                    text = str(text)
                except Exception:
                    text = ""
            retriever.add_item(it.key, text, {"layer": it.layer.name, "format": it.format, "priority": it.priority})

        hits = retriever.query(query_text, top_k=top_k, filter_fn=filter_fn)
        allowed = {k for (k, _, _) in hits}
        if not allowed:
            return
        self._items = [it for it in self._items if it.key in allowed]

    def _encode_payload(self, item: ContextItem) -> Any:
        if item.format == 'lsl' and isinstance(item.payload, CompressedLearningSession):
            return item.payload.to_lsl()
        if item.format == 'adl' and isinstance(item.payload, CompressedAgentBrief):
            return item.payload.to_adl()
        if item.format == 'opl' and isinstance(item.payload, CompressedOptimizationTrace):
            return item.payload.to_opl()
        if item.format in ('text', 'json'):
            return item.payload
        # Fallback to str()
        return str(item.payload)

    def _compress_item(self, item: ContextItem) -> CompressionResult:
        if item._compressed is None:
            obj = self._encode_payload(item)
            item._compressed = self.engine.compress(obj)
        return item._compressed

    def assemble(self, max_total_bytes: Optional[int] = None) -> Dict[str, Any]:
        total_limit = min(self.total_budget, max_total_bytes or self.total_budget)
        used_total = 0
        used_layer: Dict[ContextLayer, int] = {l: 0 for l in ContextLayer}

        selected: List[Dict[str, Any]] = []

        # Sort by layer order then priority desc, then stable by key
        layer_order = {l: i for i, l in enumerate([ContextLayer.GLOBAL, ContextLayer.DOMAIN, ContextLayer.SESSION, ContextLayer.LOCAL])}
        sorted_items = sorted(
            self._items,
            key=lambda it: (layer_order[it.layer], -it.priority, it.key),
        )

        for it in sorted_items:
            comp = self._compress_item(it)
            size = len(comp.data)
            if used_total + size > total_limit:
                continue
            if used_layer[it.layer] + size > self.per_layer_budget[it.layer]:
                continue
            selected.append({
                'key': it.key,
                'layer': it.layer.name,
                'format': it.format,
                'encoding': comp.method,
                'size': size,
                'data': comp.data,
            })
            used_total += size
            used_layer[it.layer] += size

        result = {
            'total_bytes': used_total,
            'per_layer_bytes': {k.name: v for k, v in used_layer.items()},
            'entries': selected,
        }

        # Optional MLflow tracking for assembly
        try:
            with tracking_run('context_assemble'):
                log_metrics({
                    'entries': float(len(selected)),
                    'total_bytes': float(used_total),
                    **{f'layer_bytes_{k}': float(v) for k, v in result['per_layer_bytes'].items()},
                })
        except Exception:
            pass

        return result

