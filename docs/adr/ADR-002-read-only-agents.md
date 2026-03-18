# ADR-002: Read-Only Agents by Default

**Date:** 2026-03-15
**Status:** Accepted

## Context
Federal deployments require least-privilege access. Agents that can write
data create audit liabilities and compliance risks under NIST 800-53 AC-6.

## Decision
All agent nodes are read-only by default. Write operations require:
1. Explicit RBAC gate (operator role minimum)
2. A separate ADR documenting the write scope
3. Human-in-the-loop approval step in the graph

## Consequences
- CapabilityViolationError raised on any out-of-manifest tool call
- NIST AC-6 (Least Privilege) satisfied by design
- Retriever node can only call ai_search_read — never ai_search_write

## Interview answer
"Sandboxing is not a policy — it's an enforced code path. The Retriever
raises CapabilityViolationError if anything outside its manifest is
attempted. I have a test that deliberately triggers it."
