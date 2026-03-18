# ADR-005: Overlapping Window Chunking Strategy

**Date:** 2026-03-15
**Status:** Accepted

## Context
Chunking strategy directly determines what the model can reason about.
Fixed-length chunking creates boundary artifacts that cause false refusals.
The eval harness showed 59.1% refusal rate on specific technical queries
in Meridian — traced to coarse chunking (2 chunks/article average).

## Decision
Overlapping windows: 512 tokens per chunk, 10% overlap (~51 tokens).
Every chunk carries full metadata: source_doc_id, chunk_index, site_id,
document_title, pull_id, chunk_length.

## Consequences
- ~15-20% more chunks than fixed-length (acceptable storage cost)
- Boundary artifacts eliminated — technical queries answer correctly
- Chunk metadata enables source attribution in citation panel
- Minimum chunk length: 100 tokens. Maximum: 600 tokens.

## Interview answer
"Context engineering starts at ingest. Chunk boundaries determine what
the model can reason about. I diagnosed Meridian's 59% refusal rate on
technical queries back to chunking — overlapping windows fixed it."
