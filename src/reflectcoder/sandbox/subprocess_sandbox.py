from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from reflectcoder.schemas import TestResult

# Isolation strategy for v0.1: a fresh temp directory per task plus a wall-clock
# timeout. Good enough for trusted Python fixtures; Docker replaces this once
# we run untrusted code or SWE-bench. See docs/adr/0003-sandbox-choice.md.


class SubprocessSandbox:
    def __init__(self, timeout_s: float = 20.0):
        self._timeout_s = timeout_s

    def run_tests(self, source_files: dict[str, str], test_files: dict[str, str]) -> TestResult:
        with tempfile.TemporaryDirectory(prefix="reflectcoder_") as tmp:
            workdir = Path(tmp)
            self._materialize(workdir, source_files)
            self._materialize(workdir, test_files)

            started = time.monotonic()
            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "pytest", "-x", "--tb=short", "-q"],
                    cwd=workdir,
                    capture_output=True,
                    text=True,
                    timeout=self._timeout_s,
                )
            except subprocess.TimeoutExpired as e:
                return TestResult(
                    passed=False,
                    stdout=e.stdout or "",
                    stderr=f"TIMEOUT after {self._timeout_s}s",
                    returncode=-1,
                    duration_s=self._timeout_s,
                )
            finally:
                # tempdir cleans itself; nothing to do
                pass

            duration = time.monotonic() - started
            return TestResult(
                passed=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
                duration_s=duration,
            )

    @staticmethod
    def _materialize(root: Path, files: dict[str, str]) -> None:
        for rel, content in files.items():
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

    @staticmethod
    def ensure_pytest_available() -> bool:
        return shutil.which(sys.executable) is not None
