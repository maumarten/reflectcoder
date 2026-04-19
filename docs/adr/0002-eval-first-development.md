# ADR-0002: Eval-first development

**Status:** accepted
**Date:** 2026-04-18

## Context

Most AI-coding-agent demos show one cherry-picked success on camera. When hired
to build such an agent in production, the first question an engineer is asked
is: *how do you know it works?* The honest answer requires an eval harness that
can be rerun, scored, and compared across revisions.

Building features first and evals later creates two problems:

1. Every change risks a silent regression that nobody notices.
2. Claims like "the memory system improves performance" become unverifiable
   opinions instead of measurable deltas.

## Decision

The eval harness is the spine of this project. No agent feature ships without:

1. A baseline number on the fixture set, captured *before* the feature.
2. A post-feature number on the same fixture set, using the same model and
   hyperparameters.
3. The report JSON committed under `docs/evals/` so history is auditable.

Concretely: the first commit includes the harness + a deliberately dumb
`StubAgent` (one-shot LLM call, no reflection, no memory). That is the floor.
Every subsequent agent must beat it on the same tasks — otherwise the added
complexity is not paying for itself and we delete it.

## Consequences

- Writing fixtures is part of feature work, not a separate chore.
- Early fixtures are hand-crafted (3 bugs in v0.1). They scale to a SWE-bench
  Lite subset by v0.5.
- Every PR includes a before/after score table. Reviewers can demand one.
- Occasionally we will kill features that looked smart but did not move the
  numbers. This is the point.
