from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class Task(BaseModel):
    """A single coding challenge the agent must solve.

    The `source_files` are shown to the agent. The `test_files` are hidden and
    only used by the harness to score the agent's patch.
    """

    task_id: str
    title: str
    problem: str
    source_files: dict[str, str]
    test_files: dict[str, str]
    tags: list[str] = Field(default_factory=list)
    difficulty: Literal["easy", "medium", "hard"] = "easy"


class Patch(BaseModel):
    """The agent's proposed fix: a full rewrite of one or more source files."""

    files: dict[str, str]
    rationale: str = ""


class TestResult(BaseModel):
    passed: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    duration_s: float = 0.0


class RunResult(BaseModel):
    """One end-to-end attempt at one task."""

    task_id: str
    agent: str
    model: str
    passed: bool
    iterations: int = 1
    total_tokens: int = 0
    wall_clock_s: float = 0.0
    patch: Patch | None = None
    test_result: TestResult | None = None
    error: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvalReport(BaseModel):
    """Aggregate of many RunResults, written to disk after each eval invocation."""

    agent: str
    model: str
    n_tasks: int
    n_passed: int
    pass_rate: float
    total_tokens: int
    total_wall_clock_s: float
    results: list[RunResult]
    run_dir: Path
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
