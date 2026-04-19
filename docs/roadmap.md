# Roadmap

Each milestone lists the new capability and the eval question it must answer.
No milestone is "done" until the eval delta is captured in `docs/evals/`.

## v0.1 — Baseline (current)

- Eval harness + `StubAgent` one-shot baseline + 3 hand-crafted fixtures.
- Eval question: *what pass rate does a single LLM call achieve on these bugs?*

## v0.2 — Reflective loop

- Plan → patch → test → reflect cycle with a max-iteration circuit breaker.
- Short-term scratchpad shared across iterations.
- Eval question: *does iterating with test feedback beat one-shot?*

## v0.3 — Failure memory

- Every failure is embedded and stored in ChromaDB with root-cause extraction.
- Before each new attempt, similar past failures are retrieved into the
  planner's context.
- Eval question: *does the agent improve measurably as the failure library
  grows across runs?*

## v0.4 — Observability

- Self-hosted Langfuse for trace, cost, and prompt-version tracking.
- Per-task cost and latency surfaced in the eval report.
- Eval question: *what is cost-per-passed-task, and how does it move with each
  feature?*

## v0.5 — SWE-bench Lite subset

- Scale from 3 hand-crafted fixtures to 50 tasks from SWE-bench Lite.
- Docker-backed sandbox replaces the subprocess sandbox.
- Eval question: *does the agent generalise beyond the hand-crafted set?*

## v1.0 — UI

- Next.js dashboard: live trace view, failure museum, ablation chart across
  agent versions.
- Reproducible demo via `docker compose up`.
