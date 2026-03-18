# ADR-007: Streaming Responses

**Date:** 2026-03-15
**Status:** Accepted

## Context
Non-streaming queries show a blank screen for 9+ seconds (p95 latency).
First perceived response time is the primary UX latency signal.
Azure OpenAI supports streaming. FastAPI supports StreamingResponse.

## Decision
FastAPI StreamingResponse on /query endpoint.
Azure OpenAI stream=True on all LLM calls.
First token target: <1 second from query submission.

## Consequences
- p95 wall-clock latency unchanged; perceived latency drops to ~1s
- Streaming changes the demo experience entirely — critical for live demos
- Token budget enforcement still required (stream can run long)

## Interview answer
"Streaming is the highest visual-impact change I could make. p95 latency
stays the same but the user sees the first token in under a second instead
of watching a blank screen for 9 seconds."
