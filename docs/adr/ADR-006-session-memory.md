# ADR-006: Session Memory Scoped to Conversation Window

**Date:** 2026-03-15
**Status:** Accepted

## Context
Follow-up queries that reference prior context fail without session memory.
In Meridian's eval, "Can you give me an example?" had a 54% refusal rate
because the follow-up chip fired a standalone RAG query with no prior context.

## Decision
InMemorySessionStore: TTL=1800s, keyed by session_id (UUID).
Prior answer + retrieved chunks passed as session_context in AgentState.
Session context is cleared on TTL expiry — no cross-session leakage.

Episodic memory (user-scoped, Cosmos DB, keyed by Entra OID) is the
next architectural layer — deferred until auth is working.

## Consequences
- Follow-up context pass rate: 0/4 → 4/4 (eval harness target)
- TTL prevents stale context from influencing unrelated queries
- Satisfies NIST SC-4 (Information in Shared Resources) — no leakage

## Interview answer
"Session memory is scoped to the conversation window. I measured the
before/after in the eval harness — follow-up context pass rate went
from 0% to 100% after wiring session_context into AgentState."
