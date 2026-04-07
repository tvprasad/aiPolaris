# aiPolaris — Technical Walkthrough
### Prasad Thiriveedi · VPL Solutions LLC

---

## Slide 1 — What Problem Does aiPolaris Solve?

Enterprise and federal operators need AI answers they can **audit, replay, and trust**.

Most agentic systems today are:
- Non-deterministic (different answer every run)
- Opaque (no trace of *why* a tool was called)
- Write-happy (agents can do damage)
- Single-environment (won't deploy into Azure Government)

aiPolaris was built to eliminate all four of these problems — by design, not by configuration.

---

## Slide 2 — The Architecture in One Sentence

> **A three-node LangGraph DAG where every node owns exactly its own state slice, every tool call is manifest-checked, and every execution is fully traceable.**

```
POST /query
    │
    ▼
[Auth + RBAC middleware]          ← Entra ID token, per-endpoint RBAC
    │
    ▼
[Create AgentState + trace_id]    ← fresh trace on every invocation
    │
    ▼
[Planner]  → sub_tasks            ← decompose query, no data access
    │
    ▼
[Retriever] → retrieved_chunks    ← ai_search_read only, confidence-gated
    │
    ▼
[Synthesizer] → answer, citations ← assemble + cite, no tool access
    │
    ▼
StreamingResponse (SSE)
```

Every node appends a `StepRecord` to `trace.step_log` — immutable, hashed, timestamped.

---

## Slide 3 — Step-by-Step: Query Execution

### Step 1 — Request arrives at `POST /query`

```http
POST /query
Authorization: Bearer <Entra ID JWT>
{"query": "What are the FedRAMP High controls for incident response?"}
```

FastAPI middleware validates the bearer token: **signature, expiry, audience, issuer** — all four, every time.

---

### Step 2 — AgentState is created

```python
state = AgentState(
    query="What are the FedRAMP High controls...",
    session_context={"last_query": "...", "last_answer": "..."},  # from SessionStore
    user_oid="<oid-from-token>",
    sub_tasks=[],
    retrieved_chunks=[],
    answer="",
    citations=[],
    trace=TraceContext(),  # fresh trace_id = uuid4()
)
```

**Key insight:** `trace_id` is the thread that connects every downstream log, audit record, and replay artifact. Nothing leaves the system without it.

---

### Step 3 — Planner node runs

**Owns:** `sub_tasks`
**Cannot touch:** retrieval, data sources, any other state field

```python
# planner_node calls GPT-4o at temperature=0
sub_tasks = [
    "FedRAMP High incident response controls",
    "IR-1 through IR-10 control requirements",
    "Mandatory incident reporting timelines"
]
state["sub_tasks"] = sub_tasks
# Appends StepRecord → input_hash, output_hash, latency_ms
```

Temperature=0 is not a suggestion — it is the mechanism behind the 95% replay match guarantee.

---

### Step 4 — Retriever node runs

**Owns:** `retrieved_chunks`
**Allowed tools:** `ai_search_read` only (manifest-enforced)

```python
check_capability(RETRIEVER_MANIFEST, "ai_search_read")   # ✓ passes
check_capability(RETRIEVER_MANIFEST, "ai_search_write")  # ✗ raises CapabilityViolationError
```

For each sub-task, hybrid semantic search runs against the Azure AI Search index (owned by aiNexus — aiPolaris reads, never writes):

- Query type: `semantic`
- Reranker score threshold: **0.60** — chunks below this are dropped
- Deduplication: by source document
- Returns: top-5 chunks sorted by reranker score

**Confidence gate** — if no chunks survive the threshold: Synthesizer receives an empty list → structured refusal. No hallucination path exists.

---

### Step 5 — Synthesizer node runs

**Owns:** `answer`, `citations`
**Allowed tools:** none (operates on state only)

```python
# GPT-4o receives:
#   - system prompt (hash-pinned in prompts.lock)
#   - user query
#   - retrieved chunks [1]...[5] with title, source, content
#   - session context (prior Q&A if present)
#
# Returns JSON: { "answer": "...", "citations": [...] }

if answer == "INSUFFICIENT_CONTEXT" or not chunks:
    return "I don't have enough information...", []
```

Citations are extracted from the LLM's own JSON output — never inferred, never fabricated.

---

### Step 6 — TraceContext is complete

```json
{
  "trace_id": "a3f8c1d2-...",
  "steps": [
    {
      "node": "Planner",
      "input_hash": "9f3a2b1c",
      "tool_calls": [],
      "output_hash": "4e7d2a9f",
      "latency_ms": 412.3,
      "timestamp": "2026-04-07T14:23:01.004Z"
    },
    {
      "node": "Retriever",
      "input_hash": "4e7d2a9f",
      "tool_calls": ["ai_search_read"],
      "output_hash": "b2c1e8d4",
      "latency_ms": 318.7,
      "timestamp": "2026-04-07T14:23:01.423Z"
    },
    {
      "node": "Synthesizer",
      "input_hash": "b2c1e8d4",
      "tool_calls": [],
      "output_hash": "7a3f9c2d",
      "latency_ms": 1124.6,
      "timestamp": "2026-04-07T14:23:01.742Z"
    }
  ]
}
```

A compliance officer can take this `trace_id`, replay the execution, and get **identical output** — because the model, prompts, and temperature are all pinned.

---

## Slide 4 — The Three Guarantees

| Guarantee | Mechanism |
|---|---|
| **Determinism** | GPT-4o temperature=0, prompt hash-pinning (`prompts.lock`) |
| **Containment** | `CapabilityViolationError` before every out-of-manifest tool call |
| **Auditability** | `StepRecord` per node — input hash, output hash, latency, timestamp |

---

## Slide 5 — Capability Sandboxing Deep Dive

Every node declares a manifest at module level. Before executing any tool, `check_capability()` validates the call:

```python
RETRIEVER_MANIFEST = {
    "node": "Retriever",
    "allowed_tools": ["ai_search_read"],
}

# This call passes:
check_capability(RETRIEVER_MANIFEST, "ai_search_read")

# This call raises immediately — before any network call:
check_capability(RETRIEVER_MANIFEST, "ai_search_write")
# → CapabilityViolationError: 'ai_search_write' not in Retriever manifest
```

This means a compromised or misconfigured node **cannot write data** even if the underlying SDK would allow it. The enforcement is in Python, before the Azure SDK is invoked.

---

## Slide 6 — GCCH Deployment

Federal deployments require Azure Government (`*.azure.us` endpoints). aiPolaris achieves this with **zero code changes**:

```bash
terraform workspace select gcch
terraform apply
# All endpoints switch: OpenAI, AI Search, Key Vault → *.azure.us
```

ADR-003 forbids hardcoded commercial URLs anywhere in application code. Every endpoint is resolved from Terraform workspace variables at deploy time.

---

## Slide 7 — Eval Acceptance Criteria

| Metric | Target | Status |
|---|---|---|
| p95 latency | < 4,000 ms | ✓ |
| p50 latency | < 1,500 ms | ✓ |
| Avg confidence | > 0.75 | ✓ |
| Correct refusal rate | 100% | ✓ |
| Incorrect refusal rate | < 10% | ✓ |
| Follow-up pass | 4/4 | ✓ |
| Sandbox tests | 100% | ✓ |
| Replay match rate | ≥ 95% | ✓ |

---

## Slide 8 — Where aiPolaris Fits

```
aiNexus         → owns the AI Search index (Graph API, ADLS pipeline)
    │
    └── aiPolaris → reads the index, orchestrates agents, produces answers
                        │
                        └── Meridian → governance layer, confidence gating,
                                        MCP tool server, audit trail UI
```

aiPolaris is the **orchestration layer**. It does not own data (aiNexus does). It does not govern retrieval quality (Meridian does). It executes the query plan, enforces capability boundaries, and produces a traceable answer.

---

## Slide 9 — Key Decisions (ADR Summary)

| ADR | Decision |
|---|---|
| ADR-001 | LangGraph stateful DAG — each node owns explicit state slices |
| ADR-002 | All agents READ-ONLY by default — `CapabilityViolationError` on any violation |
| ADR-003 | GCCH via Terraform workspace — one variable switches all endpoints |
| ADR-004 | `TraceContext` on every invocation — `trace_id` + `StepRecord` per node |
| ADR-008 | Prompt hash-pinning — `prompts.lock`, ADR bump required before any change |

---

## Slide 10 — What's Next

- **Session memory** (ADR-006) — TTL-scoped, session-keyed, no cross-session leakage
- **Streaming responses** (ADR-006) — SSE tokens + citations via `StreamingResponse`
- **Agent spec export** (ADR-010) — machine-readable capability manifest for external orchestrators
- **products.vplsolutions.com** — public catalog listing aiPolaris as Beta → Production

---

*"Control precedes generation. Observability precedes scale. Governance precedes automation."*
— VPL Solutions
