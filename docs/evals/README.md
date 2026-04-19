# Eval history

Every version of the agent is scored on the same fixture set, with the report
committed here so the history is auditable. See
[ADR-0002: Eval-first development](../adr/0002-eval-first-development.md).

| Version | Agent        | Fixtures | Pass | Pass rate | Tokens | Wall clock | Report |
|---------|--------------|----------|------|-----------|--------|------------|--------|
| v0.1    | `stub`       | 3        | 3    | 100.0%    | 1336   | 3.4s       | [v0.1_baseline.json](v0.1_baseline.json) |

## Reading the v0.1 baseline

The stub agent (one-shot LLM call, no reflection, no memory) solves all three
hand-crafted fixtures on `llama-3.3-70b-versatile`. This is expected and
informative: canonical Python bugs (off-by-one, floor division, mutable
default) are squarely in the training distribution of any modern 70B model.

Implication for v0.2: a reflective loop cannot demonstrate its value on
fixtures the baseline already aces. v0.2 must introduce harder fixtures
(multi-bug tasks, tasks whose specification is clarified only by the test
output) so that the reflective delta over the baseline is visible and
defensible.
