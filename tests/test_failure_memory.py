"""Unit tests for the failure memory store.

Uses ``HashingEmbedder`` so these run without torch / sentence-transformers.
The hashing embedder is deterministic across processes, so similarity rankings
are stable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from reflectcoder.memory import FailureMemory, HashingEmbedder


@pytest.fixture
def memory(tmp_path: Path) -> FailureMemory:
    m = FailureMemory(tmp_path / "failures.db", embedder=HashingEmbedder(dim=256))
    yield m
    m.close()


def test_fresh_store_is_empty(memory: FailureMemory):
    assert memory.count() == 0
    assert memory.retrieve(problem="anything", k=3) == []


def test_remember_then_retrieve_top_k(memory: FailureMemory):
    memory.remember(
        task_id="bug_parse_csv",
        problem="parse a CSV line with quoted fields",
        rationale="split on comma",
        stderr_excerpt="AssertionError: embedded comma inside quotes",
        reflection="Need a quote-aware state machine; split() is wrong.",
    )
    memory.remember(
        task_id="bug_path",
        problem="normalize a POSIX path with .. segments",
        rationale="pop on ..",
        stderr_excerpt="IndexError: pop from empty list",
        reflection="Bound .. popping at the root; don't pop past index 0.",
    )
    assert memory.count() == 2

    hits = memory.retrieve(
        problem="parse a CSV line handling quotes",
        stderr_excerpt="embedded comma inside quoted field",
        k=2,
    )
    assert len(hits) == 2
    # The CSV-related row should rank first against a CSV query.
    assert hits[0].task_id == "bug_parse_csv"
    assert 0.0 <= hits[0].similarity <= 1.0 + 1e-6
    assert hits[0].similarity >= hits[1].similarity


def test_retrieve_respects_exclude_task_id(memory: FailureMemory):
    memory.remember(
        task_id="bug_csv_a",
        problem="csv parsing with quotes",
        rationale="x",
        stderr_excerpt="AssertionError",
        reflection="r1",
    )
    memory.remember(
        task_id="bug_csv_b",
        problem="csv parsing with different quoting rules",
        rationale="y",
        stderr_excerpt="AssertionError",
        reflection="r2",
    )
    hits = memory.retrieve(
        problem="csv parsing", k=5, exclude_task_id="bug_csv_a"
    )
    assert {h.task_id for h in hits} == {"bug_csv_b"}


def test_remember_skips_empty_reflection(memory: FailureMemory):
    rid = memory.remember(
        task_id="bug",
        problem="whatever",
        rationale="x",
        stderr_excerpt="x",
        reflection="   ",
    )
    assert rid == -1
    assert memory.count() == 0


def test_clear_empties_store(memory: FailureMemory):
    memory.remember(
        task_id="t",
        problem="p",
        rationale="x",
        stderr_excerpt="x",
        reflection="r",
    )
    assert memory.count() == 1
    memory.clear()
    assert memory.count() == 0


def test_persistence_across_instances(tmp_path: Path):
    db = tmp_path / "failures.db"
    m1 = FailureMemory(db, embedder=HashingEmbedder(dim=256))
    m1.remember(
        task_id="t",
        problem="p",
        rationale="x",
        stderr_excerpt="x",
        reflection="r",
    )
    m1.close()

    m2 = FailureMemory(db, embedder=HashingEmbedder(dim=256))
    try:
        assert m2.count() == 1
        hits = m2.retrieve(problem="p", k=1)
        assert len(hits) == 1
        assert hits[0].task_id == "t"
    finally:
        m2.close()


def test_different_embedders_do_not_cross_retrieve(tmp_path: Path):
    db = tmp_path / "failures.db"
    m1 = FailureMemory(db, embedder=HashingEmbedder(dim=256))
    m1.remember(
        task_id="t",
        problem="p",
        rationale="x",
        stderr_excerpt="x",
        reflection="r",
    )
    m1.close()

    # A different embedder (different dim => different vector space) should
    # not match against the previously-stored rows.
    m2 = FailureMemory(db, embedder=HashingEmbedder(dim=128))
    try:
        assert m2.count() == 1  # the row is there...
        assert m2.retrieve(problem="p", k=5) == []  # ...but not retrievable
    finally:
        m2.close()


def test_to_prompt_block_is_one_line_and_capped(memory: FailureMemory):
    memory.remember(
        task_id="bug_x",
        problem="p",
        rationale="x",
        stderr_excerpt="stderr " * 500,
        reflection="reflection " * 500,
    )
    hits = memory.retrieve(problem="p", k=1)
    assert len(hits) == 1
    block = hits[0].to_prompt_block()
    assert "task `bug_x`" in block
    # No unbounded content in the prompt block.
    assert len(block) < 1500
