# ADR-004: TraceContext on Every Graph Invocation

**Date:** 2026-03-15
**Status:** Accepted

## Context
Federal compliance requires audit trails (NIST AU-2). Deterministic
re-playable execution requires that every invocation is traceable.

## Decision
Every graph invocation gets a trace_id (UUID4). Every node appends a
StepRecord: node_name, input_hash, tool_calls, output_hash, latency_ms,
timestamp. The trace log is serialized to JSON in the audit log.

## Consequences
- Given trace_id + pinned model + pinned prompts = reproducible output
- Incident response: "what did the agent do at 14:32 UTC?" is answerable
- Satisfies NIST AU-2 (Audit Events) and IR-4 (Incident Handling)

## Interview answer
"Every graph invocation has a trace_id. Every node logs what it read,
what tools it called, and what it returned. The system is re-playable
from any trace_id — that's deterministic execution by design."
