"""
SC.1-08: Vector-based context retrieval with optional Faiss backend.

- Uses HashingVectorizer for embeddings (no fit required) when available.
- If scikit-learn is not installed, falls back to a simple hashing-based vectorizer.
- If faiss is available, builds an index for fast search; otherwise falls back to
  NumPy cosine similarity.
"""
from __future__ import annotations

from typing import List, Optional, Tuple, Dict, Any

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover - optional dep
    faiss = None  # type: ignore

import numpy as np

try:
    from sklearn.feature_extraction.text import HashingVectorizer  # type: ignore
    SK_AVAILABLE = True
except Exception:  # pragma: no cover
    HashingVectorizer = None  # type: ignore
    SK_AVAILABLE = False


class _SimpleHasher:
    """Lightweight hashing vectorizer fallback (no external deps).
    - Lowercases and splits on whitespace
    - Hashes tokens into n_features bins and L2 normalizes
    """

    def __init__(self, n_features: int = 256):
        self.n_features = n_features

    def transform(self, docs: List[str]) -> np.ndarray:
        mats = []
        for text in docs:
            vec = np.zeros(self.n_features, dtype=np.float32)
            for tok in (text or "").lower().split():
                h = (hash(tok) % self.n_features)
                vec[h] += 1.0
            # L2 normalize
            nrm = np.linalg.norm(vec)
            if nrm > 0:
                vec = vec / nrm
            mats.append(vec)
        return np.stack(mats, axis=0)


class VectorRetriever:
    def __init__(self, n_features: int = 256, use_faiss: Optional[bool] = None):
        self.dim = n_features
        if SK_AVAILABLE:
            self.vectorizer = HashingVectorizer(n_features=n_features, alternate_sign=False, norm="l2")  # type: ignore
            self._use_simple = False
        else:
            self.vectorizer = _SimpleHasher(n_features=n_features)
            self._use_simple = True
        self.items: List[Tuple[str, np.ndarray, Dict[str, Any]]] = []
        self.index = None
        if use_faiss is None:
            use_faiss = faiss is not None
        self.use_faiss = bool(use_faiss and faiss is not None)
        if self.use_faiss:
            self.index = faiss.IndexFlatIP(self.dim)

    def _to_vec(self, text: str) -> np.ndarray:
        if self._use_simple:
            v = self.vectorizer.transform([text])[0]
        else:
            X = self.vectorizer.transform([text])
            v = X.toarray().astype(np.float32)[0]
        # Ensure normalized unit vector
        norm = np.linalg.norm(v)
        return v if norm == 0 else (v / norm)

    def add_item(self, key: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        vec = self._to_vec(text)
        metadata = metadata or {}
        self.items.append((key, vec, metadata))
        if self.use_faiss and self.index is not None:
            self.index.add(vec.reshape(1, -1))

    def query(self, text: str, top_k: int = 10, filter_fn=None) -> List[Tuple[str, float, Dict[str, Any]]]:
        q = self._to_vec(text)
        keys = [k for (k, _, _) in self.items]
        vecs = np.stack([v for (_, v, _) in self.items], axis=0) if self.items else np.zeros((0, self.dim), dtype=np.float32)
        metas = [m for (_, _, m) in self.items]

        if vecs.shape[0] == 0:
            return []

        if self.use_faiss and self.index is not None:
            # IndexFlatIP expects inner product; vectors are unit so IP==cosine
            D, I = self.index.search(q.reshape(1, -1), min(top_k, len(keys)))
            results = []
            for dist, idx in zip(D[0], I[0]):
                if idx == -1:
                    continue
                k = keys[idx]
                m = metas[idx]
                if filter_fn and not filter_fn(k, m):
                    continue
                results.append((k, float(dist), m))
            return results
        else:
            # Brute-force cosine (vectors already normalized)
            sims = (vecs @ q.reshape(-1, 1)).reshape(-1)
            order = np.argsort(-sims)
            results = []
            for idx in order[:top_k]:
                k = keys[idx]
                m = metas[idx]
                if filter_fn and not filter_fn(k, m):
                    continue
                results.append((k, float(sims[idx]), m))
            return results

