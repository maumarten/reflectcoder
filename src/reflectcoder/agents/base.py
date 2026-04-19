from __future__ import annotations

from typing import Protocol, runtime_checkable

from reflectcoder.schemas import RunResult, Task


@runtime_checkable
class Agent(Protocol):
    name: str

    def solve(self, task: Task) -> RunResult: ...
