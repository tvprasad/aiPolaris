# Presenting aiPolaris — Audience-Specific Framing

> Companion to [interview-walkthrough.md](interview-walkthrough.md).
> The walkthrough covers the full technical deep-dive.
> This doc covers how to frame the same system for different audiences.

---

## For Technical Interviews (Staff/Principal Level)

Lead with the **constraint-driven architecture** -- not the tools.

> "I didn't start with LangGraph and work backward. I started with three
> constraints: deterministic re-playability for federal audit, capability
> sandboxing that's enforced in code not policy, and zero code changes
> between commercial and GCCH. LangGraph was the only framework that gave
> me explicit state ownership per node, which is the prerequisite for all
> three."

### Key talking points

- **State ownership** -- why I rejected shared scratchpad (AutoGen) and
  permission-based approaches. Every field has exactly one owner. No node
  mutates another node's state. That's how you get deterministic traces.

- **CapabilityViolationError** -- default-deny, not default-allow.
  "Prove this agent *can't*" is stronger than "show what it can." The
  Retriever has one allowed tool: `ai_search_read`. Everything else
  raises an exception. Tested with zero tolerance.

- **Eval-driven development** -- 20 golden questions across 5 categories.
  The delta between runs IS the proof. Not "it works" -- "here's how
  much better it got, and here's the trace to prove it."

- **Lessons from Meridian** -- 54% false refusal rate on follow-up queries
  (no session context). 59% refusal rate on technical queries (coarse
  chunking). Both diagnosed from eval runs, both fixed by design in
  aiPolaris. Show you learn across systems, not just within them.

- **GCCH** -- one Terraform variable switches all endpoints. Commercial
  and GCCH are the same codebase. Teams that maintain two codebases get
  drift. One codebase, one variable.

### Questions to expect

| Question | Answer |
|----------|--------|
| Why not LangChain? | No explicit state ownership. Agents share mutable state -- impossible to audit deterministically. |
| Why linear DAG, not a loop? | Every conditional edge is a combinatorial explosion for compliance testing. Linear first, prove the acceptance bar, then add edges. |
| How do you handle hallucination? | Confidence-gated refusal. If chunks are empty or below threshold, the system refuses with a structured explanation. It does not guess. |
| How do you test agent behavior? | 20 golden questions. Correct refusal rate, incorrect refusal rate, latency percentiles, replay match rate. Acceptance criteria in CLAUDE.md. |
| What happens if a node tries something it shouldn't? | CapabilityViolationError. Immediate exception. Not a warning, not a log. The release is blocked if any sandbox test fails. |

---

## For Federal/Enterprise Stakeholders

Lead with **compliance mapping**.

> "Every design decision maps to a NIST control. TraceContext satisfies
> AU-2. Capability sandboxing satisfies AC-6. Prompt hash-pinning
> satisfies CM-3. GCCH is one Terraform variable, not a second codebase."

### NIST control mapping

| Control | Requirement | aiPolaris Implementation |
|---------|-------------|--------------------------|
| AU-2    | Audit events | TraceContext -- trace_id + StepRecord per node |
| IR-4    | Incident handling | Full execution reconstructable from trace_id |
| AC-6    | Least privilege | CapabilityViolationError -- default-deny tool manifests |
| AC-2    | Account management | RBAC middleware -- user/operator/admin roles |
| AC-5    | Separation of duties | Capability checks in middleware, never in handlers |
| CM-3    | Configuration change control | Prompt hash-pinning via prompts.lock |
| IA-5    | Authenticator management | Key Vault only -- no credentials in code or env |

### Phrases that land

- "Deterministic execution. Same input, same trace, every time."
- "Default-deny capability model. Agents prove they can't, not that they can."
- "One codebase, one variable. Commercial to GCCH with zero code changes."
- "The audit trail isn't bolted on. It's structural."

---

## For Product/Demo Audiences

Lead with the **streaming demo** and the **refusal behavior**.

> "Ask it something it shouldn't answer. Watch it refuse with a structured
> explanation, not hallucinate. Ask it something it should answer. Watch
> the first token appear in under a second. That's the difference between
> a chatbot and a governed system."

### Demo script

1. **Show the refusal** -- ask an out-of-scope question ("What's the
   weather in DC?"). The system refuses cleanly with an explanation.
   No hallucination. No made-up answer.

2. **Show the answer** -- ask a question the index can answer. First
   token appears in under a second. Citations included. Confidence
   score visible.

3. **Show the follow-up** -- ask "Can you give me an example?" The
   system uses session context from the prior answer. It doesn't
   start from scratch.

4. **Show the trace** -- pull the trace_id from the response header.
   Show the full StepRecord log: which nodes ran, what tools they
   called, input/output hashes, latency per step.

### One-liner for each audience

| Audience | One-liner |
|----------|-----------|
| CTO | "Governed AI agents with deterministic audit trails -- GCCH-ready from commit one." |
| CISO | "Default-deny capability model. Every agent invocation has a trace_id. Full replay from audit log." |
| Engineering lead | "LangGraph DAG with explicit state ownership, capability sandboxing, and an eval harness that proves behavior." |
| Federal program manager | "NIST AU-2, AC-6, CM-3 mapped. One Terraform variable for GCCH. No second codebase." |

---

## Portfolio context

When presenting aiPolaris, always frame it within the portfolio:

| Product | Role | Relationship |
|---------|------|-------------|
| Meridian | Governed RAG control plane | Retrieval + governance layer |
| aiNexus | Enterprise data pipeline | Graph API, ADLS, AI Search index |
| **aiPolaris** | **Agent orchestration** | **Reads the aiNexus index. Does not own or populate it.** |

> "Meridian taught me that follow-ups fail without session memory and
> technical queries fail without proper chunking. aiPolaris has both
> from day one -- not because I predicted the problems, but because I
> measured them in Meridian's eval runs and built the fixes into the
> next system's architecture."

---

*Control precedes generation. Observability precedes scale.
Governance precedes automation.*
