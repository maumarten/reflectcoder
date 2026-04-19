# ADR-0003: Sandbox choice — subprocess now, Docker later

**Status:** accepted
**Date:** 2026-04-18

## Context

The agent will execute code it writes. That code can be wrong, slow, or
malicious. We need an execution boundary that:

1. Cannot corrupt the host workspace (writes stay inside a temp dir).
2. Enforces a wall-clock timeout so infinite loops cannot hang the harness.
3. Is cheap to spin up — we may run hundreds of iterations during an eval.

Options considered:

- **Option A — `subprocess` with a temp CWD and timeout.**
  Cheap, cross-platform, zero setup. Gives filesystem isolation but shares the
  host Python, network, and process table.
- **Option B — Docker container per task.**
  Strong isolation (filesystem, network, resources). Much slower cold start on
  Windows (WSL2), and adds a non-trivial setup step for readers trying to
  reproduce results.
- **Option C — E2B / Modal / cloud sandbox.**
  Production-grade, but fails the $0 constraint above the free tier, and adds a
  network hop to every test run.

## Decision

Ship Option A for v0.1–v0.3. Fixtures at this stage are hand-written, trusted
Python: the threat model is "the model outputs an infinite loop", not "the
model is hostile". A subprocess with a temp CWD and wall-clock timeout handles
that exactly.

Migrate to Option B (Docker) when we onboard SWE-bench Lite in v0.5. At that
point: (a) tasks execute real-world library code we do not audit; (b) we run
hundreds of attempts per eval so a few seconds of Docker startup is amortised;
(c) the sandbox needs to deny network access by default.

## Consequences

- v0.1 readers can run `python -m reflectcoder eval` with zero infra.
- The `Sandbox` interface stays small (`run_tests(sources, tests) -> TestResult`)
  so swapping the implementation is a localised change.
- We accept that a truly hostile model could, in principle, escape the current
  sandbox. This is acceptable for the current threat model and is revisited in
  the v0.5 migration.
