"""Text embedders for the failure-memory retrieval layer.

Two implementations are shipped:

- ``SentenceTransformerEmbedder`` — wraps ``sentence-transformers/all-MiniLM-L6-v2``,
  384-dim semantic embeddings. This is the default for real runs.
- ``HashingEmbedder`` — a dependency-free fallback that uses a stable
  hashing bag-of-words into a fixed-dim sparse-ish vector. It is NOT a good
  semantic embedder; it exists so tests can exercise the full memory
  pipeline without requiring torch to be installed in CI.

Both implementations satisfy the ``Embedder`` protocol.
"""

from __future__ import annotations

import hashlib
import re
from typing import Protocol

import numpy as np

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


class Embedder(Protocol):
    """Produces a unit-length float32 vector from an input string."""

    name: str
    dim: int

    def embed(self, text: str) -> np.ndarray:  # pragma: no cover - protocol
        ...


class HashingEmbedder:
    """Deterministic, dependency-free embedder — stable across processes.

    Tokenizes, folds tokens into a fixed-size vector via a stable hash, and
    L2-normalizes. Good enough for tests of the retrieval plumbing; do not
    expect it to capture semantic similarity well.
    """

    def __init__(self, dim: int = 384):
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim
        self.name = f"hashing-{dim}"

    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in _TOKEN_RE.findall(text.lower()):
            h = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(h[:4], "little") % self.dim
            sign = 1.0 if h[4] & 1 else -1.0
            vec[idx] += sign
        n = float(np.linalg.norm(vec))
        if n > 0:
            vec /= n
        return vec


class SentenceTransformerEmbedder:
    """Semantic embedder backed by ``all-MiniLM-L6-v2`` (384-dim, ~22M params).

    Lazy-loads the model on first use so importing this module is cheap.
    The first ``embed`` call downloads weights (~90MB) to the HuggingFace
    cache, once per machine.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self._model_name = model_name
        self.name = model_name
        self.dim = 384
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            self.dim = int(self._model.get_sentence_embedding_dimension())
        return self._model

    def embed(self, text: str) -> np.ndarray:
        model = self._load()
        vec = model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vec.astype(np.float32, copy=False)


def default_embedder() -> Embedder:
    """Return the semantic embedder if torch is available, else the hashing fallback.

    This keeps CI (and first-run users without a 2GB torch install) working,
    while letting production runs pick up the real semantic model
    automatically.
    """
    try:
        import sentence_transformers  # noqa: F401
    except Exception:
        return HashingEmbedder()
    return SentenceTransformerEmbedder()
