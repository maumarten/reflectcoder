from __future__ import annotations

import time

from reflectcoder.llm import LLMClient
from reflectcoder.patch_parser import parse_patch as _parse_patch
from reflectcoder.sandbox import SubprocessSandbox
from reflectcoder.schemas import IterationStep, RunResult, Task

SYSTEM_PROMPT = """You are a precise Python bug-fixing assistant.

You will receive a problem description and one or more source files that contain a bug.
Return a JSON object with this exact shape and NOTHING ELSE:

{
  "rationale": "<1-3 sentence explanation of the bug and your fix>",
  "files": {
    "<relative/path.py>": "<full corrected file contents>"
  }
}

Strict JSON rules:
- Every string value must be double-quoted. NEVER use Python triple-quoted strings.
- Escape newlines as \\n, tabs as \\t, and double quotes as \\".
- Do not output anything outside the top-level JSON object — no prose, no code fences.

Content rules:
- Output only the files that need to change. Return their FULL contents, not a diff.
- Do not modify test files.
- Preserve existing public function signatures unless the problem explicitly asks otherwise.
- Do not add print statements, logging, or commentary inside the code.
"""


class StubAgent:
    """One-shot baseline: a single LLM call, no reflection, no memory.

    Exists to set the floor. Every smarter agent in this repo must beat it
    on the same fixture set, using the same model, or the complexity isn't
    paying for itself.
    """

    name = "stub"

    def __init__(self, llm: LLMClient, sandbox: SubprocessSandbox):
        self._llm = llm
        self._sandbox = sandbox

    def solve(self, task: Task) -> RunResult:
        started = time.monotonic()
        user_prompt = _render_task(task)

        try:
            completion = self._llm.complete(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.2,
                json_mode=True,
            )
        except Exception as e:
            return RunResult(
                task_id=task.task_id,
                agent=self.name,
                model=self._llm.model,
                passed=False,
                wall_clock_s=time.monotonic() - started,
                error=f"llm_error: {type(e).__name__}: {e}",
            )

        patch = _parse_patch(completion.text)
        if patch is None:
            return RunResult(
                task_id=task.task_id,
                agent=self.name,
                model=self._llm.model,
                passed=False,
                total_tokens=completion.total_tokens,
                wall_clock_s=time.monotonic() - started,
                error="parse_error: model did not return valid JSON patch",
            )

        merged_sources = {**task.source_files, **patch.files}
        test_result = self._sandbox.run_tests(merged_sources, task.test_files)

        step = IterationStep(
            index=0,
            patch=patch,
            test_result=test_result,
            reflection=None,
            tokens=completion.total_tokens,
        )
        return RunResult(
            task_id=task.task_id,
            agent=self.name,
            model=self._llm.model,
            passed=test_result.passed,
            total_tokens=completion.total_tokens,
            wall_clock_s=time.monotonic() - started,
            patch=patch,
            test_result=test_result,
            trace=[step],
        )


def _render_task(task: Task) -> str:
    files_blob = "\n\n".join(
        f"### {path}\n```python\n{content}\n```" for path, content in task.source_files.items()
    )
    return f"""# Problem
{task.problem}

# Source files
{files_blob}

Respond with the JSON patch object only.
"""
