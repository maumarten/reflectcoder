"""Sanity checks that do not require an LLM.

These ensure the harness plumbing (fixture loader, sandbox, schemas) works
in CI without consuming a Groq quota.
"""

from reflectcoder.config import FIXTURES_DIR
from reflectcoder.evals.harness import load_fixtures
from reflectcoder.sandbox import SubprocessSandbox


def test_fixtures_load():
    tasks = load_fixtures(FIXTURES_DIR)
    assert len(tasks) >= 3
    ids = {t.task_id for t in tasks}
    assert "bug_001_sum_first_n" in ids
    assert "bug_002_average_precision" in ids
    assert "bug_003_mutable_default" in ids


def test_buggy_source_fails_tests():
    """The shipped source code MUST fail the hidden tests; otherwise there's nothing to fix."""
    tasks = load_fixtures(FIXTURES_DIR)
    sandbox = SubprocessSandbox(timeout_s=10.0)
    for task in tasks:
        result = sandbox.run_tests(task.source_files, task.test_files)
        assert not result.passed, f"Fixture {task.task_id} passes its tests unmodified — bug missing?"


def test_known_fix_passes_tests():
    """An oracle patch must make the tests pass — validates that the harness is solvable."""
    sandbox = SubprocessSandbox(timeout_s=10.0)
    tasks = {t.task_id: t for t in load_fixtures(FIXTURES_DIR)}

    fixed_sum = {
        "calculator.py": (
            "def sum_first_n(n: int) -> int:\n"
            '    """Return the sum of the integers 1..n inclusive."""\n'
            "    total = 0\n"
            "    for i in range(1, n + 1):\n"
            "        total += i\n"
            "    return total\n"
        )
    }
    r = sandbox.run_tests(fixed_sum, tasks["bug_001_sum_first_n"].test_files)
    assert r.passed, r.stdout + r.stderr

    fixed_avg = {
        "stats.py": (
            "def average(numbers: list[int]) -> float:\n"
            '    """Return the arithmetic mean of `numbers` as a float."""\n'
            "    if not numbers:\n"
            "        return 0.0\n"
            "    return sum(numbers) / len(numbers)\n"
        )
    }
    r = sandbox.run_tests(fixed_avg, tasks["bug_002_average_precision"].test_files)
    assert r.passed, r.stdout + r.stderr

    fixed_acc = {
        "accumulator.py": (
            "def append_item(item, bucket=None):\n"
            '    """Append `item` to `bucket` and return the bucket."""\n'
            "    if bucket is None:\n"
            "        bucket = []\n"
            "    bucket.append(item)\n"
            "    return bucket\n"
        )
    }
    r = sandbox.run_tests(fixed_acc, tasks["bug_003_mutable_default"].test_files)
    assert r.passed, r.stdout + r.stderr
