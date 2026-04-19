# ADR-0004: Failure memory — SQLite + MiniLM, not Chroma

**Status:** accepted
**Date:** 2026-04-19

## Context

v0.3b introduces a persistent "failure memory": records of prior failed
attempts (problem, rationale, stderr excerpt, reflection) that can be
retrieved by semantic similarity and injected into the proposer prompt on
future tasks.

Three decisions had to be made up front:

1. Where to store rows (structured store).
2. How to embed and retrieve (vector search).
3. What content to embed (retrieval key).

## Decisions

### Store: SQLite

Rows live in a single SQLite file (`memory/failures.db`) with the embedding
persisted as a BLOB column alongside the other metadata.

- No new daemon, no new binary, no network hop.
- One file = one git-ignorable artefact per machine.
- At the scale this repo cares about (<10k rows through v0.5), a full table
  scan for retrieval is faster than shipping Chroma / pgvector / FAISS,
  each of which would also add a dependency.

Rejected: ChromaDB. The roadmap originally named it, but in practice an
embedded vector DB is overkill until the store has at least tens of
thousands of rows. We can migrate later by replaying the SQLite rows into
Chroma if we cross that threshold.

### Embedder: sentence-transformers/all-MiniLM-L6-v2

- 384-dim, ~22M params, CPU-runnable.
- Free, local, deterministic across runs (given the same model weights).
- Widely-used baseline — easy for a reader to swap for a larger model.

We keep the embedder behind a Protocol (`Embedder`) and ship a
dependency-free `HashingEmbedder` fallback. The fallback exists so the unit
tests can exercise the full memory pipeline without torch, which keeps CI
fast and keeps the core install light for users who don't want the memory
layer.

Rejected: OpenAI/Cohere embedding APIs (fails the $0 constraint on
sustained use, and adds a network hop per query). Also rejected: training
our own embedder (overkill for n<10k rows).

### Retrieval key: `problem + stderr`, not the patch code

Embedding the attempted patch would let similar code structure match, but
code tokens dominate the signal and drown out the conceptual shape of the
bug. The `problem + stderr` pairing is what actually carries the
information about *why this attempt failed* — which is what we want future
proposers to steer clear of.

## Alternatives considered and the why

- **Embed the whole iteration trace (including previous proposer output)**:
  tempting, but pollutes the vector space with JSON structure tokens and
  pushes relevant signal below the noise floor. Rejected.
- **Store multiple embeddings per row** (one for problem, one for stderr):
  cleaner semantically but doubles storage and halves retrieval-time
  parallelism. Rejected until a failure-mode analysis shows it helps.
- **Let the reflector also propose a retrieval query**: adds an LLM call
  per write. Rejected; the retrieval key is already content-rich enough.

## Consequences

- Retrieval stays simple: one `numpy` matmul, O(n * d) with n < 10k and
  d = 384 is <1ms even at the upper bound.
- Memory layer is testable without GPU / torch — CI runs green on the
  HashingEmbedder.
- If we later want cross-project memory sharing, the SQLite file is
  portable and the embedding format is self-describing (we store
  `embedding_dim` and `embedder_name` per row).
- The retrieval filters `WHERE embedder_name = ?` at query time, so
  changing embedders doesn't silently compare vectors from different
  spaces.
