"""
Basic compression engine for SC.1-01.

This module provides a minimal, dependency-tolerant abstraction over MessagePack
and Zstandard (zstd) so the codebase can compile and tests can run even if the
optional compression dependencies are not yet installed in the environment.

- If msgpack or zstandard are missing, the engine gracefully degrades to
  JSON+utf-8 bytes passthrough with a flag indicating no real compression.
- When present, MessagePack is used for binary serialization and Zstd for
  dictionary-based compression.

Note: Once you approve dependency installation, add to backend/requirements.txt:
  msgpack>=1.0,<2.0
  zstandard>=0.22,<1.0
and run pip install -r requirements.txt inside backend venv.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import json
from .tracking import log_metrics, run as tracking_run

try:
    import msgpack  # type: ignore
except Exception:  # pragma: no cover - optional in scaffolding phase
    msgpack = None  # type: ignore

try:
    import zstandard as zstd  # type: ignore
except Exception:  # pragma: no cover - optional in scaffolding phase
    zstd = None  # type: ignore


@dataclass
class CompressionResult:
    method: str  # "msgpack", "zstd+msgpack", or "noop"
    data: bytes
    ratio: Optional[float] = None  # original_size / compressed_size when known


class BasicCompressionEngine:
    """Minimal engine exposing compress/decompress helpers.

    Priority:
    - If zstd is available and a compressor provided, use zstd over msgpack bytes
    - Else if msgpack is available, return msgpack bytes
    - Else fall back to JSON bytes with method "noop"
    """

    def __init__(
        self,
        zstd_compressor: Optional["zstd.ZstdCompressor"] = None,
        zstd_dict: Optional["zstd.ZstdCompressionDict"] = None,
    ):
        self._zstd_compressor = zstd_compressor if zstd is not None else None
        self._zstd_dict = zstd_dict if zstd is not None else None

    def compress(self, obj: Any) -> CompressionResult:
        # Serialize to bytes first (msgpack preferred)
        if msgpack is not None:
            serialized = msgpack.packb(obj, use_bin_type=True)
            method = "msgpack"
        else:
            serialized = json.dumps(obj, separators=(",", ":")).encode("utf-8")
            method = "noop"

        # Optionally compress with zstd
        if self._zstd_compressor is not None:
            compressed = self._zstd_compressor.compress(serialized)
            ratio = (len(serialized) / len(compressed)) if len(compressed) else None
            res = CompressionResult(method="zstd+msgpack", data=compressed, ratio=ratio)
        else:
            res = CompressionResult(method=method, data=serialized, ratio=None)

        # Optional MLflow tracking
        try:
            with tracking_run("compression"):
                log_metrics({
                    "input_bytes": float(len(serialized)),
                    "output_bytes": float(len(res.data)),
                    "ratio": float((len(serialized) / len(res.data)) if len(res.data) else 1.0),
                }, tags={"method": res.method})
        except Exception:
            pass

        return res

    def decompress(self, comp: CompressionResult) -> Any:
        payload = comp.data

        if comp.method == "zstd+msgpack":
            if zstd is None:
                raise RuntimeError("zstandard not available to decompress data")
            # Use dictionary if available to avoid mismatch
            if self._zstd_dict is not None:
                dctx = zstd.ZstdDecompressor(dict_data=self._zstd_dict)
            else:
                dctx = zstd.ZstdDecompressor()
            payload = dctx.decompress(payload)
            # fall-through to msgpack decode

        # msgpack decode when available
        if msgpack is not None:
            try:
                return msgpack.unpackb(payload, raw=False)
            except Exception:
                # If payload was JSON, fall back below
                pass

        # Fallback JSON
        try:
            return json.loads(payload.decode("utf-8"))
        except Exception:
            # Return raw bytes as last resort
            return payload

