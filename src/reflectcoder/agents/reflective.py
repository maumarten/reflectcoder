"""Reflective agent: plan -> patch -> test -> reflect -> retry.

The value proposition: when the one-shot stub fails, the model has no way to
recover because it never sees the test output. The reflective loop gives the
model that feedback and asks it to explain, in plain words, what went wrong
and what to try next. The next proposal is primed with that reflection.

We deliberately keep the reflection in natural language rather than letting
the model emit more JSON: the job of the reflector is diagnosis, not patching,
and mixing the two muddles both.
"""

from __future__ import annotations

import time

from reflectcoder.llm import LLMClient
from reflectcoder.patch_parser import parse_patch as _parse_patch
from reflectcoder.sandbox import SubprocessSandbox
from reflectcoder.schemas import IterationStep, Patch, RunResult, Task, TestResult

PROPOSER_SYSTEM = """You are a precise Python bug-fixing assistant.

You will receive a problem description, one or more buggy source files, and —
on retries — the history of prior attempts with their test failures and
reflections. Your job: produce a patch that passes the hidden tests.

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
- Output only the files that need to change. Return their FULL contents.
- Never modify test files.
- Preserve existing public function signatures unless the problem tells you otherwise.
- No print statements, no logging, no commentary inside the code.
- If prior attempts are shown, carefully read their reflections and do not
  repeat the same mistakes.
"""

REFLECTOR_SYSTEM = """You are a debugging assistant. A patch just failed its tests.
In plain words — no code blocks — state:

1. What the patch got wrong: did it miss the bug entirely, fix it incorrectly,
   or introduce a new bug?
2. The specific construct or behaviour that is still incorrect.
3. ONE concrete change to try next. Describe the required change; do not write code.

Be precise and blunt. Stay under 120 words total.
"""

_STDERR_CAP = 1500


class ReflectiveAgent:
    name = "reflective"

    def __init__(self, llm: LLMClient, sandbox: SubprocessSandbox, max_iter: int = 3):
        if max_iter < 1:
            raise ValueError("max_iter must be >= 1")
        self._llm = llm
        self._sandbox = sandbox
        self._max_iter = max_iter

    @property
    def model(self) -> str:
        return self._llm.model

    def solve(self, task: Task) -> RunResult:
        started = time.monotonic()
        trace: list[IterationStep] = []
        prior: list[IterationStep] = []
        total_tokens = 0

        consecutive_llm_errors = 0
        for i in range(self._max_iter):
            propose_prompt = _render_proposer_prompt(task, prior)
            try:
                completion = self._llm.complete(
                    system=PROPOSER_SYSTEM,
                    user=propose_prompt,
                    temperature=0.2,
                    json_mode=True,
                )
                consecutive_llm_errors = 0
            except Exception as e:
                consecutive_llm_errors += 1
                # Treat as a recoverable iteration: reflect on the failure and
                # let the next proposal try again with corrective instructions.
                step = IterationStep(
                    index=i,
                    patch=Patch(files={}, rationale=""),
                    test_result=TestResult(
                        passed=False,
                        stderr=f"llm_error: {type(e).__name__}: {e}",
                    ),
                    reflection=(
                        "The previous LLM call failed. The most common cause is "
                        "returning Python triple-quoted strings or unescaped newlines "
                        "in JSON values. Re-emit the patch as strictly valid JSON "
                        "with double-quoted, \\n-escaped string values."
                    ),
                    tokens=0,
                )
                trace.append(step)
                prior.append(step)
                if consecutive_llm_errors >= 2:
                    return RunResult(
                        task_id=task.task_id,
                        agent=self.name,
                        model=self._llm.model,
                        passed=False,
                        iterations=len(trace),
                        total_tokens=total_tokens,
                        wall_clock_s=time.monotonic() - started,
                        trace=trace,
                        error=f"llm_error_circuit_breaker: {type(e).__name__}: {e}",
                    )
                continue
            total_tokens += completion.total_tokens

            patch = _parse_patch(completion.text)
            if patch is None:
                step = IterationStep(
                    index=i,
                    patch=Patch(files={}, rationale=""),
                    test_result=TestResult(
                        passed=False,
                        stderr="parse_error: model did not return valid JSON patch",
                    ),
                    reflection="The previous output was not a valid JSON patch. Strictly emit the specified JSON object.",
                    tokens=completion.total_tokens,
                )
                trace.append(step)
                prior.append(step)
                continue

            sources = {**task.source_files, **patch.files}
            test_result = self._sandbox.run_tests(sources, task.test_files)

            if test_result.passed:
                step = IterationStep(
                    index=i,
                    patch=patch,
                    test_result=test_result,
                    reflection=None,
                    tokens=completion.total_tokens,
                )
                trace.append(step)
                return RunResult(
                    task_id=task.task_id,
                    agent=self.name,
                    model=self._llm.model,
                    passed=True,
                    iterations=i + 1,
                    total_tokens=total_tokens,
                    wall_clock_s=time.monotonic() - started,
                    patch=patch,
                    test_result=test_result,
                    trace=trace,
                )

            # Patch failed — reflect so the next iteration can do better.
            reflection = self._reflect(task, patch, test_result)
            total_tokens += reflection.tokens
            step = IterationStep(
                index=i,
                patch=patch,
                test_result=test_result,
                reflection=reflection.text,
                tokens=completion.total_tokens + reflection.tokens,
            )
            trace.append(step)
            prior.append(step)

            # Circuit breaker: two consecutive identical patches mean we are stuck.
            if len(prior) >= 2 and prior[-1].patch.files == prior[-2].patch.files:
                break

        final = trace[-1] if trace else None
        return RunResult(
            task_id=task.task_id,
            agent=self.name,
            model=self._llm.model,
            passed=False,
            iterations=len(trace),
            total_tokens=total_tokens,
            wall_clock_s=time.monotonic() - started,
            patch=final.patch if final else None,
            test_result=final.test_result if final else None,
            trace=trace,
        )

    def _reflect(self, task: Task, patch: Patch, test_result: TestResult) -> _Reflection:
        prompt = _render_reflector_prompt(task, patch, test_result)
        try:
            completion = self._llm.complete(
                system=REFLECTOR_SYSTEM,
                user=prompt,
                temperature=0.3,
                json_mode=False,
            )
        except Exception as e:
            return _Reflection(
                text=f"(reflection unavailable: {type(e).__name__}: {e})",
                tokens=0,
            )
        return _Reflection(text=completion.text.strip(), tokens=completion.total_tokens)


class _Reflection:
    __slots__ = ("text", "tokens")

    def __init__(self, text: str, tokens: int):
        self.text = text
        self.tokens = tokens


def _render_proposer_prompt(task: Task, prior: list[IterationStep]) -> str:
    sources_blob = "\n\n".join(
        f"### {path}\n```python\n{content}\n```" for path, content in task.source_files.items()
    )
    parts = [
        f"# Problem\n{task.problem}",
        f"\n# Source files\n{sources_blob}",
    ]
    if prior:
        history = []
        for step in prior:
            history.append(
                (
                    f"## Attempt {step.index + 1} — FAILED\n"
                    f"Rationale: {step.patch.rationale}\n"
                    f"Test output (stderr excerpt):\n"
                    f"{_trim(step.test_result.stderr or step.test_result.stdout, _STDERR_CAP)}\n"
                    f"Reflection: {step.reflection or '(none)'}"
                )
            )
        parts.append("\n# Prior attempts (most recent last)\n" + "\n\n".join(history))
    parts.append("\nRespond with the JSON patch object only.")
    return "\n".join(parts)


def _render_reflector_prompt(task: Task, patch: Patch, test_result: TestResult) -> str:
    files_blob = "\n\n".join(
        f"### {path}\n```python\n{content}\n```" for path, content in patch.files.items()
    )
    stderr = _trim(test_result.stderr or test_result.stdout, _STDERR_CAP)
    return (
        f"# Problem\n{task.problem}\n\n"
        f"# Patch that failed\n{files_blob}\n\n"
        f"# Test output\n```\n{stderr}\n```\n"
    )


def _trim(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated {len(text) - limit} more chars]"
