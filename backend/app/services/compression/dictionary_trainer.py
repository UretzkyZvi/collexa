"""
Zstandard dictionary training utilities for SC.1-01.

Trains zstd dictionaries for different semantic domains. This module is
dependency-tolerant: if zstandard is unavailable, trainer methods are no-ops that
return None, allowing tests to run before dependencies are installed.
"""

from __future__ import annotations

from typing import Iterable, Optional

try:
    import zstandard as zstd  # type: ignore
except Exception:  # pragma: no cover - optional in scaffolding phase
    zstd = None  # type: ignore


class ZstdDictionaryTrainer:
    def __init__(self, dict_size: int = 8192):
        self.dict_size = dict_size

    def train(self, samples: Iterable[bytes]) -> Optional["zstd.ZstdCompressionDict"]:
        if zstd is None:
            return None
        sample_list = [s for s in samples if s]
        if not sample_list:
            return None
        dict_data = zstd.train_dictionary(self.dict_size, sample_list)
        return dict_data

    def build_compressor(self, dictionary: Optional["zstd.ZstdCompressionDict"]):
        if zstd is None or dictionary is None:
            return None
        return zstd.ZstdCompressor(dict_data=dictionary)

