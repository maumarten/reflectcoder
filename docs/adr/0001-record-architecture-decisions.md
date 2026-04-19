# ADR-0001: Record architecture decisions

**Status:** accepted
**Date:** 2026-04-18

## Context

AI-engineering projects drift quickly. A choice that looked obvious in week 1
(e.g. "use Groq") is the thing we second-guess in week 4 when rate limits bite.
Future readers of this repo — hiring managers, collaborators, or myself — need
to understand *why* a decision was made, not just what the current state is.

## Decision

Significant architectural choices are captured as ADRs in `docs/adr/`, numbered
sequentially, using the format: Context → Decision → Consequences.

A change is "significant" if answering "why did you do it this way?" requires
more than pointing at code — i.e. it reflects a tradeoff between alternatives.

## Consequences

- Small overhead per decision, repaid many times over when revisiting later.
- ADRs are versioned with the code, so they cannot silently drift out of sync.
- We do **not** document every trivial choice; ADRs are for hinge points.
