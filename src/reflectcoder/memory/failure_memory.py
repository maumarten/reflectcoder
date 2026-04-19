"""SQLite-backed failure memory with top-k cosine retrieval.

The store is append-only during a run: the agent writes a failure record
whenever a patch fails its tests AND a reflection was produced. Before each
proposer call on a new task, the agent queries the store with
``(problem + latest stderr)`` and injects the top-k similar prior failures
into the prompt.

We deliberately keep the ANN layer simple: embeddings are L2-normalized at
insert time, cosine similarity is just a dot product, and retrieval is a
matrix-vector multiply in numpy. At this scale (<10k rows) this is faster
than spinning up FAISS or Chroma and removes a dependency.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from reflectcoder.memory.embedder import Embedder

_SCHEMA = """
CREATE TABLE IF NOT EXISTS failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    task_id TEXT NOT NULL,
    problem TEXT NOT NULL,
    rationale TEXT NOT NULL,
    stderr_excerpt TEXT NOT NULL,
    reflection TEXT NOT NULL,
    embedding BLOB NOT NULL,
    embedding_dim INTEGER NOT NULL,
    embedder_name TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_failures_task_id ON failures(task_id);
"""


@dataclass(frozen=True)
class FailureRecord:
    id: int
    created_at: str
    task_id: str
    problem: str
    rationale: str
    stderr_excerpt: str
    reflection: str
    similarity: float = 0.0

    def to_prompt_block(self) -> str:
        return (
            f"- task `{self.task_id}` (similarity {self.similarity:.2f})\n"
            f"  stderr excerpt: {_one_line(self.stderr_excerpt, 240)}\n"
            f"  reflection: {_one_line(self.reflection, 400)}"
        )


class FailureMemory:
    """Append-only store of (problem, patch rationale, stderr, reflection) rows.

    Thread-unsafe by design — each eval run creates one instance.
    """

    def __init__(self, db_path: Path, embedder: Embedder):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._embedder = embedder
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    @property
    def path(self) -> Path:
        return self._db_path

    @property
    def embedder_name(self) -> str:
        return self._embedder.name

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM failures").fetchone()
        return int(row[0])

    def clear(self) -> None:
        self._conn.execute("DELETE FROM failures")
        self._conn.commit()

    def remember(
        self,
        *,
        task_id: str,
        problem: str,
        rationale: str,
        stderr_excerpt: str,
        reflection: str,
    ) -> int:
        if not reflection.strip():
            # No diagnostic signal — don't pollute the store.
            return -1
        text = _embedding_text(problem, stderr_excerpt)
        vec = self._embedder.embed(text)
        blob = vec.astype(np.float32, copy=False).tobytes()
        created_at = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            """INSERT INTO failures (
                created_at, task_id, problem, rationale,
                stderr_excerpt, reflection, embedding, embedding_dim, embedder_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                created_at,
                task_id,
                problem,
                rationale,
                stderr_excerpt,
                reflection,
                blob,
                int(vec.shape[0]),
                self._embedder.name,
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def retrieve(
        self,
        *,
        problem: str,
        stderr_excerpt: str = "",
        k: int = 3,
        exclude_task_id: str | None = None,
        min_similarity: float = 0.0,
    ) -> list[FailureRecord]:
        if k <= 0:
            return []
        text = _embedding_text(problem, stderr_excerpt)
        query_vec = self._embedder.embed(text).astype(np.float32, copy=False)

        where = ""
        params: tuple = ()
        if exclude_task_id is not None:
            where = " WHERE task_id != ? AND embedder_name = ?"
            params = (exclude_task_id, self._embedder.name)
        else:
            where = " WHERE embedder_name = ?"
            params = (self._embedder.name,)

        rows = self._conn.execute(
            "SELECT id, created_at, task_id, problem, rationale, "
            "stderr_excerpt, reflection, embedding, embedding_dim "
            "FROM failures" + where,
            params,
        ).fetchall()
        if not rows:
            return []

        matrix = np.stack(
            [np.frombuffer(r[7], dtype=np.float32) for r in rows], axis=0
        )
        sims = matrix @ query_vec  # both sides already L2-normalized

        order = np.argsort(-sims)
        out: list[FailureRecord] = []
        for idx in order:
            sim = float(sims[idx])
            if sim < min_similarity:
                break
            r = rows[idx]
            out.append(
                FailureRecord(
                    id=int(r[0]),
                    created_at=str(r[1]),
                    task_id=str(r[2]),
                    problem=str(r[3]),
                    rationale=str(r[4]),
                    stderr_excerpt=str(r[5]),
                    reflection=str(r[6]),
                    similarity=sim,
                )
            )
            if len(out) >= k:
                break
        return out

    def dump_recent(self, n: int = 10) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, task_id, created_at, reflection FROM failures "
            "ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [
            {"id": r[0], "task_id": r[1], "created_at": r[2], "reflection": r[3]}
            for r in rows
        ]

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self) -> "FailureMemory":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def _embedding_text(problem: str, stderr_excerpt: str) -> str:
    parts = [problem.strip()]
    if stderr_excerpt.strip():
        parts.append("TEST OUTPUT:")
        parts.append(stderr_excerpt.strip())
    return "\n".join(parts)


def _one_line(text: str, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def load_as_json(path: Path) -> list[dict]:
    """Read-only helper for debugging / docs generation."""
    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute(
            "SELECT id, created_at, task_id, problem, rationale, "
            "stderr_excerpt, reflection, embedder_name FROM failures ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": r[0],
            "created_at": r[1],
            "task_id": r[2],
            "problem": r[3],
            "rationale": r[4],
            "stderr_excerpt": r[5],
            "reflection": r[6],
            "embedder_name": r[7],
        }
        for r in rows
    ]


__all__ = ["FailureMemory", "FailureRecord", "load_as_json"]
