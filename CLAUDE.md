# CLAUDE.md — aiPolaris
# Last updated: 2026-03-15
# Ruthlessly refine after every mistake.
# This is the compounding mechanism — every rule here prevents a class of error automatically.

## Project objective
Federal-grade multi-agent orchestration framework.
Planner → Retriever → Synthesizer DAG.
Deterministic, re-playable, capability-sandboxed, GCCH-ready from day 1.

## Portfolio relationship
Meridian  : governed RAG control plane (retrieval, eval, governance)
aiNexus   : enterprise data pipeline (Graph API, ADLS, AI Search index)
aiPolaris : agent orchestration layer (LangGraph DAG, sandboxing, audit trail)
aiPolaris reads the aiNexus index. It does not own or populate it.

## Stack
Backend  : Python 3.12, FastAPI (async, streaming), LangGraph 0.2+
LLMs     : Azure OpenAI (GPT-4o, temperature=0 — deterministic execution)
Retrieval: Azure AI Search (read-only — aiNexus owns the index)
Auth     : Azure AD Entra ID, MSAL, RBAC middleware per endpoint
Infra    : Terraform, workspaces: commercial | gcch
Tests    : pytest, pytest-asyncio, unittest.mock for Azure SDK calls
Eval     : offline harness, golden_questions.json, p50/p95/refusal metrics

## ADR constraints — never violate without updating an ADR first
- ADR-001: LangGraph — stateful DAG, explicit state ownership per node
- ADR-002: Agents READ-ONLY by default. CapabilityViolationError on any violation.
- ADR-003: GCCH Terraform workspaces — env variable toggles all endpoints, not code
- ADR-004: TraceContext on every invocation — trace_id + StepRecord per node
- ADR-005: Prompt hash-pinning — prompts.lock, ADR bump required before any change
- ADR-006: Streaming — FastAPI StreamingResponse + Azure OpenAI stream=True
- ADR-007: Session memory — TTL=1800s, keyed by session_id, no cross-session leakage

## Role-specific rules

### ML Engineer mode
- Plan mode (Shift+Tab) before every node. Never implement without a plan.
- Every node appends StepRecord to state.trace.step_log before returning.
- No node writes state fields outside its declared ownership.
- CapabilityViolationError raised before any out-of-manifest tool call.
- AgentState schema locked before any node implemented.

### Security mode
- Challenge mode after every security-critical implementation.
- No credentials in code. Key Vault only. Managed identity always.
- Every Entra ID token validation checks: signature, expiry, audience, issuer.
- RBAC checks in middleware only — never in route handlers.

### DevOps mode
- terraform plan reviewed before terraform apply. No exceptions.
- Every main merge generates a release record. No exceptions.
- Image tags digest-pinned (sha256) — never mutable tags.

## Never do
- Hardcode any Azure endpoint or credential
- Skip CapabilityViolationError check before any tool call
- Import inside function bodies
- Use sync blocking calls in async FastAPI route handlers
- Write a node that mutates state outside its declared ownership
- Merge without all CI gates passing
- Commit without running `mypy agent/ pipeline/ api/ --strict` locally — same command CI runs. Never commit without mypy clean.

## Eval acceptance criteria (Artifact 4)
- p95 latency        : < 4,000 ms
- p50 latency        : < 1,500 ms
- avg confidence     : > 0.75
- correct refusal    : 100% on out-of-scope
- incorrect refusal  : < 10%
- follow-up pass     : 4/4 (100%)
- sandbox tests      : 100% pass (zero tolerance)
- replay match rate  : >= 95%

## Lessons learned — add after every mistake
# Format: [date]: [what went wrong] → [rule added]
# [2026-04-08]: LCEL changes shipped with mypy errors (max_tokens kwarg, untyped dict, missing annotations). CI caught it; local pre-commit did not. → mypy --strict is now a locked pre-commit rule.
