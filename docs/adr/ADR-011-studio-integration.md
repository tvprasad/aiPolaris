# ADR-011: Studio Integration — aiPolaris as Second Query Mode

**Date:** 2026-04-09
**Status:** Accepted
**Project:** aiPolaris + Meridian Studio

## Context

aiPolaris is a headless API: Planner → Retriever → Synthesizer DAG with SSE
streaming, session memory, and full trace output (StepRecord per node).
It has no user interface.

Meridian Studio (studio.vplsolutions.com) is the existing operator UI for
the VPL Solutions AI platform. It already exposes a Query page (Meridian
RAG) and an Agent Query page (Meridian ReAct agent).

A second query mode surfaced inside Studio gives operators a unified
interface for both Meridian (governed RAG, stateless, fast) and aiPolaris
(multi-step DAG, session-aware, citation-backed). This also strengthens the
platform demo story: one UI, two architecturally distinct AI engines,
visible reasoning at every stage.

The integration must not couple the two backends — Studio connects to
aiPolaris via its public API only. No shared state, no shared deployment.

## Options Considered

### Option A: Dual-mode toggle on existing Query page (selected)
- Single page with mode toggle: RAG Query (Meridian) | Agent Query (aiPolaris)
- Auto-routing hint based on question complexity — user confirms, not silent
- Stage progress indicators driven by SSE events from aiPolaris DAG
- Interactive trace visualization: clickable Planner → Retriever → Synthesizer DAG
- Session memory indicator with explicit Clear Session control
- Actionable failure messages naming the failing stage
- `VITE_AIPOLARIS_URL` env var — never hardcoded

### Option B: Dedicated page (AIPolarisQuery.tsx) (rejected)
- Cleaner isolation but adds nav complexity
- Operators would need to context-switch between pages for comparison queries
- Rejected — single page with mode toggle provides richer UX and demo value

### Option C: Embed aiPolaris in AgentQuery.tsx (rejected)
- Conflates two different agents (ReAct vs DAG) under one label
- Rejected — architecturally misleading, breaks the product distinction

## Decision

**Option A — dual-mode toggle on the Query page.** A single surface with
explicit mode context teaches operators the architectural difference while
minimising nav complexity. The interactive trace visualization is the
primary differentiator: it makes the DAG execution tangible and auditable
in a way no generic AI chat interface offers.

## Consequences

**Positive:**
- Studio becomes the unified operator interface for the full VPL Solutions
  AI platform — one login, two engines, full audit trail
- Interactive trace visualization differentiates Studio from generic AI
  chat UIs — operators see sub-tasks, retrieved chunks, and citations per node
- Stage progress indicators (Planning... Retrieving... Synthesizing...) set
  latency expectations and make aiPolaris's multi-step cost visible and justified
- Session memory indicator + Clear Session button eliminates confusion about
  follow-up context scope
- Auto-routing hint (not silent switching) preserves operator trust —
  the system suggests, the operator decides
- Actionable failure messages ("Retriever found 0 results — try broadening
  the question") reduce support burden

**Negative / tradeoffs:**
- Query page becomes more complex — careful component design required to
  avoid cognitive overload for non-technical operators
- Two API clients in Studio (meridianApi + aipolarisApi) — different base
  URLs, different auth headers, different response shapes
- aiPolaris SSE streaming requires the same EventSource handling already
  used for Meridian's /query endpoint — low risk but must be verified

**GCCH implications:**
- `VITE_AIPOLARIS_URL` must resolve to the GCCH aiPolaris endpoint when
  Studio is deployed in GCCH — same pattern as `VITE_MERIDIAN_URL`
- No cross-cloud API calls: Studio in GCCH calls aiPolaris in GCCH only
- Trace data (StepRecord) rendered in Studio must not be cached in
  localStorage or sessionStorage — memory only, cleared on session end

## NIST mapping

AU-2 (Audit Events): Interactive trace visualization surfaces the full
  StepRecord audit trail to operators in real time — not just in logs.
AC-5 (Separation of Duties): Mode toggle makes node ownership boundaries
  explicit — Planner/Retriever/Synthesizer capabilities visible per stage.
SA-17 (Developer Security Architecture): Two independent API clients
  enforce backend separation — Studio cannot call aiPolaris internals.
SC-4 (Information in Shared Resources): Clear Session button provides
  explicit session boundary control, preventing cross-query context leakage.

## Interview answer

"Rather than building a separate UI for aiPolaris, we integrated it as a
second query mode in Meridian Studio. The key design decision was the
interactive trace visualization — operators can click through the DAG and
see exactly what the Planner decomposed, what the Retriever found per
sub-task, and how the Synthesizer assembled the answer. That makes the
multi-step cost of Agent Query visible and justified, and it turns the
audit trail from a compliance artifact into a live debugging tool. No
generic AI chat interface does that."
