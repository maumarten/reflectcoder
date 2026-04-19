# ReflectCoder

A self-improving coding agent that learns from its failures. Built to demonstrate production-grade AI engineering: agentic loops, memory hierarchies, reflection, sandboxed execution, and an eval harness that quantifies every claim.

## Why this exists

Most "AI coding agent" demos show one cherry-picked success. ReflectCoder ships with a reproducible eval harness so you can see exactly how well it performs — and watch it improve as its failure memory grows.

## The claim

> A coding agent with a reflective failure memory outperforms a one-shot baseline on the same tasks, using the same model, within the same wall-clock budget.

This repo is the experiment that proves or disproves that claim. Results are published in [`docs/evals/`](docs/evals/).

## Architecture at a glance

```
               ┌────────────────────────────────────┐
               │              CLI / UI              │
               └──────────────────┬─────────────────┘
                                  │
               ┌──────────────────┴─────────────────┐
               │          Eval Harness              │  ← the spine
               │  (loads fixtures, scores runs)     │
               └──────────────────┬─────────────────┘
                                  │
            ┌─────────────────────┴────────────────────┐
            │                  Agent                   │
            │   plan → patch → test → reflect → remember
            └──┬───────────┬──────────────┬────────────┘
               │           │              │
         ┌─────┴────┐ ┌────┴─────┐ ┌──────┴───────┐
         │   LLM    │ │ Sandbox  │ │   Memory     │
         │ (Groq /  │ │ (subproc │ │ (SQLite +    │
         │  Ollama) │ │  /Docker)│ │  ChromaDB)   │
         └──────────┘ └──────────┘ └──────────────┘
```

## Roadmap

- **v0.1 — Baseline** (this commit): eval harness + stub one-shot agent + 3 fixtures. Gives us a score to beat.
- **v0.2 — Reflective loop**: plan → patch → test → reflect cycle. Short-term scratchpad, max iterations, circuit breaker.
- **v0.3 — Failure memory** (shipped as v0.3a + v0.3b): every failure embedded and stored; similar past failures retrieved before each new attempt.
- **v0.4 — Observability**: Langfuse traces, per-task cost, prompt versioning.
- **v0.5 — SWE-bench Lite subset**: scale from hand-crafted fixtures to 50-task public benchmark.
- **v1.0 — UI**: live trace view, failure museum, ablation dashboard.

## Quickstart

```bash
# 1. Clone and install
pip install -e .

# 2. Configure (free Groq key: https://console.groq.com)
cp .env.example .env
# edit .env and set GROQ_API_KEY

# 3. Run baseline eval
python -m reflectcoder eval --agent stub

# 4. Run the reflective agent (plan -> patch -> test -> reflect -> retry)
python -m reflectcoder eval --agent reflective --max-iter 3

# 5. Run the reflective-memory agent (retrieves similar prior failures, writes
#    new ones back to a SQLite + sentence-transformers store).
#    Requires the optional 'memory' extras: pip install -e ".[memory]"
python -m reflectcoder eval --agent reflective-memory --reset-memory
python -m reflectcoder eval --agent reflective-memory   # second run benefits from the first

# 6. Inspect the memory store
python -m reflectcoder memory
```

## Design principles

- **Eval-first**: no feature ships without a measurable delta on the fixture set. See [`docs/adr/0002-eval-first-development.md`](docs/adr/0002-eval-first-development.md).
- **$0 stack**: Groq free tier, Ollama for offline fallback, local ChromaDB, local Langfuse. No paid dependency gates a reader from reproducing results.
- **Reproducible**: `docker compose up` brings the full stack. Fixtures are deterministic. Eval runs are seeded.

## Status

**v0.3b** — failure memory layer shipped. The `reflective-memory` agent persists each failed attempt's `(problem, rationale, stderr excerpt, reflection)` to a SQLite store, embedded with `sentence-transformers/all-MiniLM-L6-v2`, and on each proposer call retrieves the top-k most similar prior failures from *other* tasks as prompt-time hints. Cold ablation (empty store) matches `reflective` as expected (7/8). Warm ablation (store populated from the cold run) is deferred: the cold run consumed the Groq free-tier daily TPD on `llama-3.3-70b-versatile`, so the warm run is pending the daily reset. See [`docs/evals/v0.3b_ablation.md`](docs/evals/v0.3b_ablation.md) and [`docs/adr/0004-failure-memory-design.md`](docs/adr/0004-failure-memory-design.md).

**v0.3a** — fixture set expanded from 5 to 8 with harder cases (specific error-message discipline, under-specified path edge cases, stateful CSV parsing). Ablation: stub 6/8, reflective 7/8. The reflective loop's retry-after-reflection behaviour recovered `bug_007_path_normalize` cleanly on iteration 2 — the first time in this repo's history the loop made an auditable, iteration-driven win on a published fixture. `bug_008_csv_parser_quoted` remains unsolved by both agents, leaving real room for v0.3b's failure memory to earn its value. See [`docs/evals/v0.3a_ablation.md`](docs/evals/v0.3a_ablation.md).

Tracking remaining milestones in [`docs/roadmap.md`](docs/roadmap.md).

## License

MIT
