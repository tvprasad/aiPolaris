# One Query. Two Systems. The Whole Story.
### Internal Use Only · VPL Solutions LLC

---

> A federal operator types one question:
> **"What are the incident response requirements for FedRAMP High systems?"**
>
> Here is exactly what happens — and why every decision was made the way it was.

---

Each step below has two tiers. Read whichever fits your context:

- **Plain** — no code, no jargon. If you need to re-read it, it's not plain enough.
- **Technical** — the class, the file, the design decision, the tradeoff.

---

## Act 1 — aiPolaris: The Orchestration Layer

---

### Step 1 — The question arrives

**Plain**
The operator sends the question to the system over a secure connection. Nothing happens yet — the system doesn't trust anyone until it checks who's asking.

**Technical**
`POST /query` hits `api/routers/query.py`. FastAPI routes the request before any application logic runs. The handler is declared async — no thread blocking on I/O. The request body is validated against `QueryRequest` (Pydantic v2) at the framework layer before the handler function is called.

**What:** A structured HTTP request carrying the question text and an optional session identifier.
**Why:** Separation of transport from logic — the router knows nothing about agents or retrieval.
**When:** Every query, every time, without exception.

---

### Step 2 — Identity is verified

**Plain**
Before the question goes anywhere, the system checks the caller's credentials — like a security desk that validates your badge before you enter the building. It checks four things: Is the badge real? Has it expired? Was it issued for this building? Was it issued by the right authority? All four, every time.

**Technical**
Auth middleware (`api/middleware/auth.py`) validates the Entra ID bearer token on: signature (RS256), expiry (`exp` claim), audience (`aud` must match this application's client ID), and issuer (`iss` must match the expected tenant). A failure on any one returns HTTP 401 immediately — the request does not proceed.

**What:** Cryptographic verification of the caller's identity token.
**Why:** Trust nothing at the boundary. An unsigned or expired token could be a replay attack or a leaked credential.
**When:** Every request except `/health`. No exceptions in the middleware stack.

---

### Step 3 — Role is checked

**Plain**
Knowing *who* you are is not enough. The system also checks *what you're allowed to do*. A regular user can ask questions. An operator can also load new documents. An admin can access audit records. These are different keys to different rooms.

**Technical**
`require_capability("query")` is a FastAPI dependency on the route — `api/middleware/rbac.py`. It reads the `roles` claim from the validated token and checks it against `ROLE_CAPABILITIES`: `user → [query]`, `operator → [query, ingest, settings]`, `admin → [query, ingest, settings, eval, audit]`. This check lives in middleware — never inside route handlers — so there is no path to bypass it by adding a new route without also adding the dependency.

**What:** Role-to-capability mapping enforced before any business logic runs.
**Why:** Centralizing access control in middleware means one place to audit, one place to change. A route handler that implements its own access check is a route handler that can forget to.
**When:** On every request. The user's `oid` (object identifier from Entra ID) is attached to `request.state` for downstream use.

---

### Step 4 — A unique execution context is created

**Plain**
The system opens a fresh notebook for this question — blank pages, a unique serial number on the cover, and the caller's identity written on the first line. Every observation made during this execution will go into this notebook. Nothing from any other question's notebook can get in.

**Technical**
`create_initial_state()` in `agent/graph.py` instantiates `AgentState` — a Python `TypedDict` that is the single source of truth for the entire execution. It includes a `TraceContext` with a freshly generated `trace_id` (UUID4). The `user_oid` from the auth token and `session_context` from `InMemorySessionStore` (if a `session_id` was provided) are sealed into state here. No node can replace these fields — they are read-only from this point forward.

**What:** `AgentState` — a typed, immutable-at-entry container for the entire execution.
**Why:** Shared mutable state without ownership rules is how distributed bugs happen. Declaring field ownership up front — in code, not a document — makes violations detectable at review time.
**When:** Once per query invocation, before any node runs.

---

### Step 5 — The question is broken apart

**Plain**
The question "What are the incident response requirements for FedRAMP High systems?" is actually three questions hiding in one. A specialist reads it and breaks it into specific search terms before anyone opens a filing cabinet. That way the search is precise — not a single vague query, but a focused list of exactly what to look for.

**Technical**
`planner_node` in `agent/nodes/planner.py` calls Azure OpenAI GPT-4o at `temperature=0` with the system prompt loaded from `agent/prompts/planner_system.txt` (hash-pinned). It returns a JSON array of sub-tasks — up to four, enforced by slice. On parse failure it falls back to `[query]` — never raises to caller. Session context (prior Q&A) is included in the user message if present, so follow-up questions are decomposed with awareness of the conversation.

The Planner's manifest: `allowed_tools: []` — no data access, no external calls.

**What:** Query decomposition — one question becomes a list of precise retrieval queries.
**Why:** A vague query produces vague results. Breaking the question into sub-tasks sharpens every downstream search. Temperature=0 makes this decomposition deterministic — the same question produces the same sub-tasks every time.
**When:** Immediately after state creation. The Planner writes only `sub_tasks`. It cannot touch any other state field.

---

### Step 6 — Evidence is gathered

**Plain**
Now a second specialist takes the search terms and goes to the filing cabinet — read-only access, no pen, no ability to move or change anything. For each search term, they find the most relevant pages in the knowledge base, score them by how well they actually answer the question (not just whether they contain the right words), and bring back only the strongest matches.

**Technical**
`retriever_node` in `agent/nodes/retriever.py` calls `check_capability(RETRIEVER_MANIFEST, "ai_search_read")` before any network call — `CapabilityViolationError` raised immediately on any other tool attempt. It then runs hybrid semantic search against Azure AI Search for each sub-task: `query_type="semantic"`, `semantic_configuration_name="default"`, `top=5`. Azure's semantic reranker scores each result. Results are deduplicated by `source` document. `DefaultAzureCredential` (managed identity) handles auth — no API key in code.

**What:** Hybrid semantic search — keyword matching + vector similarity + semantic reranking.
**Why:** Keyword search alone misses synonyms and paraphrases. Vector similarity alone can return topically related but contextually wrong results. Semantic reranking re-scores by actual relevance to the query — not just lexical overlap.
**When:** Once per sub-task. The Retriever writes only `retrieved_chunks`. It cannot write answers, citations, or any other field.

---

### Step 7 — The confidence gate

**Plain**
Not every page the search returns is worth reading. Some are only loosely related — the right topic, wrong context. The system filters them out before passing anything to the person who writes the answer. If nothing is good enough, the writer never gets called at all.

**Technical**
Each search result carries a `@search.reranker_score` from Azure AI Search's semantic reranker (range: 0–4). The Retriever enforces a minimum of `0.60` — anything below is dropped. Results surviving the gate are sorted descending by score and capped at top-5 overall.

If `retrieved_chunks` is empty after filtering, the Synthesizer receives an empty list and returns the hardcoded refusal string — GPT-4o is never called. Correct refusal rate: 100% on out-of-scope questions.

**What:** A numeric confidence threshold that separates signal from noise before generation.
**Why:** Passing weak evidence to a language model does not produce a cautious answer — it produces a confident-sounding wrong answer. The gate eliminates the hallucination path structurally, not by instruction.
**When:** Applied to every result from every sub-task search, before anything reaches the Synthesizer.

---

### Step 8 — The answer is assembled

**Plain**
A third specialist receives only the pre-screened pages and writes a direct answer, citing every source by page and document. They are not allowed to use any external resources — only what was handed to them. If the pages don't contain enough to answer, they say so clearly.

**Technical**
`synthesizer_node` in `agent/nodes/synthesizer.py` calls GPT-4o with `response_format={"type": "json_object"}` — the model must return `{"answer": "...", "citations": [...]}`. `temperature=0`. The system prompt is hash-pinned. If `answer == "INSUFFICIENT_CONTEXT"` or parsing fails, the hardcoded refusal string is returned and `citations` is set to `[]`. The Synthesizer's manifest: `allowed_tools: []` — it operates on state only, no external calls.

**What:** Grounded generation — the model reasons over retrieved evidence, not its training data.
**Why:** Citations are not cosmetic. They are the only mechanism that lets a compliance officer verify that an answer is grounded in authoritative source documents rather than the model's parametric memory.
**When:** Only after the Retriever has populated `retrieved_chunks`. Writes only `answer` and `citations`.

---

### Step 9 — The refusal path

**Plain**
If the search found nothing reliable, the system does not try anyway. It returns a plain, honest statement: "I don't have enough information in my knowledge base to answer this question accurately." No guess. No fabrication. A clean, logged, traceable refusal.

**Technical**
Two triggers:
1. `retrieved_chunks` is empty (nothing survived the confidence gate) — Synthesizer returns the constant `_INSUFFICIENT` without calling GPT-4o.
2. GPT-4o returns `"INSUFFICIENT_CONTEXT"` as the answer value — same constant returned.

The refusal string is a Python constant (`agent/nodes/synthesizer.py:26`) — not generated, not variable, not subject to prompt injection. The `StepRecord` is still appended with the refusal outcome. The `trace_id` is still valid. The execution is fully auditable.

**What:** A structural refusal path that bypasses generation entirely.
**Why:** A system that always produces an answer is a liability. A system that knows when to refuse — and proves it was the right call via the trace — is defensible.
**When:** Triggered by empty retrieval results or an explicit LLM signal. Not by a confidence score — confidence gating happens upstream.

---

### Step 10 — The execution log is sealed

**Plain**
Every specialist wrote a timestamped entry in the shared notebook before handing off — what they received, what they produced, and how long it took. The notebook is now complete. Anyone with the serial number can open it and reconstruct exactly what happened.

**Technical**
Each node appended a `StepRecord` to `state["trace"].step_log` before returning. Each record contains: `node_name`, `input_hash` (SHA-256 of inputs), `output_hash` (SHA-256 of outputs), `tool_calls` (list of tool names actually called), `latency_ms`, `timestamp` (UTC ISO 8601). The full `TraceContext` — three `StepRecord` entries under one `trace_id` — is returned in the final state and included in the `done` SSE event.

**What:** An immutable, hashed execution log tied to a single `trace_id`.
**Why:** Hash-chaining inputs to outputs means any tampering is detectable. The `trace_id` is the anchor for compliance review, replay verification, and incident investigation.
**When:** Every node, every execution, without opt-out.

---

### Step 11 — Conversation memory is updated

**Plain**
If this was part of an ongoing conversation, the system remembers what was just asked and answered — for up to 30 minutes of inactivity. The next question can build on this one. After 30 minutes of silence, the memory clears automatically. One user's conversation never bleeds into another's.

**Technical**
`session_store.set()` in `agent/memory/session.py` — `InMemorySessionStore` keyed by `session_id` (UUID). Stores `last_query`, `last_answer`, `last_chunks`. TTL: 1800 seconds, enforced on every `.get()` call via `last_accessed` timestamp. Each `session_id` is isolated — `get()` returns `None` for expired or unknown keys. Module-level singleton shared across all requests in the process.

**What:** Short-term, session-scoped conversational memory.
**Why:** Without context, follow-up questions read as standalone queries. "What about IR-4 specifically?" has no meaning without the prior question. Session context passes the prior Q&A into the Planner so it decomposes follow-ups correctly.
**When:** Updated after every successful graph invocation. Read at the start of the next invocation if a matching `session_id` is provided.

---

### Step 12 — The answer streams to the caller

**Plain**
Instead of waiting for the full answer to be ready before sending anything, the system starts delivering words as soon as they are ready — like a person reading a document out loud while still reading ahead. The caller sees the first words within about a second. At the end, the system sends a list of sources and the notebook's serial number.

**Technical**
`StreamingResponse` in `api/routers/query.py` with `media_type="text/event-stream"`. The answer is chunked at 20 characters and delivered as `{"type": "token", "content": "..."}` SSE events. On completion: `{"type": "done", "citations": [...], "trace_id": "...", "latency_ms": ...}`. Response headers carry `X-Session-Id` and `X-Trace-Id` from the moment the connection opens — before the first token. On error: `{"type": "error", "message": "..."}`.

**What:** Server-Sent Events (SSE) streaming of the answer token by token.
**Why:** A 2-second wait with no feedback feels like a failure. Streaming first-token latency is typically under 1 second — the caller knows the system is working. The `done` event carries everything needed for the citation panel and audit reference.
**When:** For every `/query` response, regardless of answer length.

---

## Act 2 — Meridian: The Governance Layer

---

### Step 13 — The answer enters the control plane

**Plain**
aiPolaris produces an answer. Meridian decides what to do with it. These are different jobs handled by different systems. Meridian's job is governance — it checks whether the answer meets the quality bar before it reaches the operator, and it provides the tools to act on it.

**Technical**
Meridian's `services/control/` contains `handle_query` and `handle_query_stream` — the RAG control plane entry points. The provider abstraction (`providers/base.py` — abstract `LLMProvider`) keeps the control plane model-agnostic. `AzureOpenAIProvider`, `OllamaProvider`, and Claude via MCP all implement the same interface. Meridian version: 0.16.0. Stack: Python 3.12, FastAPI 0.134, SQLAlchemy 2.x, Pydantic v2.

**What:** The governance layer that enforces quality policy regardless of which LLM produced the answer.
**Why:** Separating orchestration (aiPolaris) from governance (Meridian) means either system can be upgraded independently. The control plane's confidence policy does not care which model answered.
**When:** Every query that flows through Meridian's API surface.

---

### Step 14 — Confidence is calibrated

**Plain**
Raw similarity scores from a search engine are not the same as "how confident should I be in this answer." A score of 0.7 from one index does not mean the same thing as 0.7 from another. Meridian runs a calibration step that translates raw scores into true probabilities — a number you can actually act on.

**Technical**
`CalibratedScorer` in `services/calibration/calibrator.py` uses isotonic regression (`sklearn.isotonic.IsotonicRegression`) to map raw L2-distance similarity scores to calibrated probabilities in [0, 1]. Trained on labeled query-relevance pairs (minimum 10 pairs). Loaded at startup from a persisted model file (`joblib`). If no model is fitted, raw scores pass through unchanged — backward-compatible. Module-level singleton via `get_scorer()`.

**What:** Isotonic regression calibration — raw retrieval scores mapped to interpretable probabilities.
**Why:** A retrieval score of 0.65 is not "65% confident." It is a distance metric in a vector space. Calibration trains a monotonic function from historical labeled data so the output is a true probability — one you can compare across queries and set policy thresholds against.
**When:** Applied to retrieval scores before threshold enforcement. Skipped gracefully if no calibration model exists.

---

### Step 15 — The threshold decides: answer or refuse

**Plain**
Every answer has a confidence score. Meridian has a minimum. If the score doesn't meet it, the answer does not go out — the system refuses and says why. This threshold is set in configuration, not buried in code, so it can be adjusted as the system learns.

**Technical**
Static threshold enforcement in `services/control/` — a calibrated confidence score below the configured threshold returns HTTP 422 with a structured refusal body. This is not a soft suggestion — it is an enforced contract. The threshold is configurable via `settings` (not hardcoded). Refusals are logged with `trace_id`, confidence score, and category. Every refusal is a data point for calibration improvement.

**What:** A hard confidence gate that turns a low-confidence answer into a governed refusal.
**Why:** An AI system that answers confidently when it shouldn't is more dangerous than one that refuses. The threshold makes "I don't know" a first-class outcome — logged, traceable, and improvable.
**When:** Applied after calibration, before the answer leaves the control plane.

---

### Step 16 — Citations are surfaced

**Plain**
Every answer that passes the threshold comes with its sources — the exact documents it was drawn from, with titles and last-modified dates. The operator can click through to the source. The answer is not just an answer; it is a claim with evidence attached.

**Technical**
Citations are extracted from the Synthesizer's JSON output (`agent/nodes/synthesizer.py`) — not generated separately, not inferred by Meridian. They are passed through the `done` SSE event and surfaced in Meridian's citation panel UI. Each citation carries: `title`, `source` (document path), `last_modified`. The citation panel is part of Meridian Studio (`studio.vplsolutions.com`).

**What:** Source attribution — every answer traceable to its evidence documents.
**Why:** Without citations, the operator has to trust the system. With citations, the operator can verify the system. In a federal environment, verification is not optional.
**When:** Delivered with every answer that passes the confidence threshold.

---

### Step 17 — The ReAct agent handles operational follow-up

**Plain**
If the operator's question is not about documents but about live systems — "Is there an open incident right now?" or "What changed in the last 24 hours?" — a different specialist handles it. This one reasons step by step: form a hypothesis, check a tool, update the hypothesis, check another tool, then answer. It logs every step.

**Technical**
`run_agent()` in `services/agent/executor.py` — a ReAct (Reason + Act) loop using GPT-4o function calling (`tool_choice="auto"`, `tools=TOOL_DEFINITIONS`). The LLM selects a tool and arguments. `execute_tool()` runs it. The result is appended to the message history. The LLM reasons and either calls another tool or returns a final answer. Max steps: 5 (configurable). Deadline: `settings.AGENT_TIMEOUT_S`. Every step is persisted to Azure SQL as `AgentStep`. Budget-exhausted: one final no-tools LLM call to synthesize findings.

**What:** A multi-step reasoning loop that uses live tools to answer operational questions.
**Why:** Document retrieval cannot answer "Is there an open P1 incident?" — that requires querying a live system. The ReAct pattern separates reasoning (LLM) from execution (tools) so each can be governed independently.
**When:** Invoked for operational queries routed to the AI Operations Agent. Not used for document Q&A.

---

### Step 18 — Every tool call passes through 12 gates

**Plain**
When the ReAct agent wants to use a tool — look up an incident, query a database, update a record — that request does not go directly to the tool. It passes through a 12-stage checkpoint. Each stage checks one thing. Any stage can block the request. A write operation requires a human to have already approved it, explicitly, by name and step number.

**Technical**
Tool Gateway (`tool_gateway/pipeline/`) — a sequential pipeline of stages in `stages.py`:

1. Request parsing
2. Token validation — `X-Agent-Id` and `X-Trace-Id` required
3. Agent registration check — agent must exist in registry with matching role
4. Manifest check — tool must be in `agent.manifest.allowed_tools`
5. Boundary enforcement — `research` namespace: read tools only; `exec` namespace: write tools only
6. Input schema validation — Pydantic model per tool; write tools require `plan_id`, `approval_ref`, `step_number`
7. SQL query safety — `SELECT`/`WITH` only for read tools; DDL/DCL blocked for all
8. Approval verification (write tools) — approval must exist, be unexpired, have authorized approver role, pass separation of duties check, plan hash must match, tool + target must match approved scope
9. Rate limiting — sliding window per agent, `retry_after_s` in error payload
10. Tool execution
11. Output redaction
12. Audit logging — SHA-256 input/output hashes, latency, `trace_id`

**What:** A 12-stage sequential enforcement pipeline governing every tool invocation.
**Why:** No single check is sufficient. Defense in depth — if a manifest is misconfigured, boundary enforcement catches it. If boundary enforcement is misconfigured, approval verification catches write attempts. Stages cannot be skipped or reordered.
**When:** Every tool call from every agent, every time. No bypass path exists in the code.

---

### Step 19 — Claude Desktop connects via MCP

**Plain**
An engineer using Claude Desktop on their laptop can ask Meridian questions directly — as naturally as typing in a chat window. The integration is standardized: Claude speaks a protocol that Meridian implements, so there is no custom connector to maintain.

**Technical**
`server_mcp/` implements both HTTP and stdio MCP (Model Context Protocol) servers. `integrations/claude_desktop_config.example.json` provides the Claude Desktop configuration. `integrations/semantic_kernel.py` provides a Semantic Kernel plugin for enterprise .NET integrations. Meridian is a model-agnostic control plane — the same governance layer serves Claude, GPT-4o, and Ollama through the same `LLMProvider` abstraction.

**What:** MCP (Model Context Protocol) — a standardized interface for connecting LLM clients to governed tool servers.
**Why:** A custom connector per client is maintenance overhead that scales badly. MCP is an open standard. Any MCP-compatible client — Claude Desktop, custom tooling, future clients — connects to the same server without code changes.
**When:** When an MCP-compatible client is configured to use Meridian as a tool server.

---

## Epilogue — The Audit

---

### Step 20 — The compliance officer looks up the trace

**Plain**
Three weeks later, an auditor needs to verify that the answer given to a federal operator was drawn from authoritative sources, not fabricated. They have the notebook's serial number — the `trace_id` — from the original response header. They look it up. The full execution is there: every step, every input, every output.

**Technical**
`trace_id` from the `X-Trace-Id` response header maps to a `TraceContext` with three `StepRecord` entries. Each record carries `input_hash` and `output_hash` (SHA-256). `AgentStep` records in Azure SQL carry the same `trace_id`. The full chain: HTTP request → auth claims → `AgentState` → Planner output → Retriever output → Synthesizer output → streaming response. Every link is hashed and timestamped.

**What:** End-to-end audit trail — one `trace_id` reconstructs the entire execution.
**Why:** In a federal environment, "trust me" is not a compliance posture. The audit trail is the proof that the system behaved as designed. The hashes are the tamper evidence.
**When:** Available immediately after every execution. No special export or reporting step required.

---

### Step 21 — Replay produces the identical answer

**Plain**
The auditor does not just read the log. They run the same question again — same everything — and get the same answer, word for word. This is the proof that the system is deterministic: not lucky, not approximately right, but provably identical under the same conditions.

**Technical**
Replay match rate target: ≥ 95%. Enabled by three pinned variables: model (`gpt-4o`, fixed deployment), prompts (SHA-256 hash in `prompts.lock`, CI enforces no drift), temperature (`0` — no sampling randomness). The `input_hash` on each `StepRecord` allows verification that the replay received identical inputs. If the index has changed since the original execution, results may differ — this is expected and documented.

**What:** Deterministic replay — identical inputs + pinned model + pinned prompts = identical output.
**Why:** A system that cannot replay its own history cannot defend its own decisions. Determinism is the technical foundation of auditability.
**When:** Any time a `trace_id` is used to re-execute with the same parameters.

---

## The Three Lines

Every design decision in both systems traces back to one of three principles:

---

> **"Control precedes generation."**

You do not let a language model call tools freely and hope for the best. You declare what each agent is allowed to do — in code, not policy — and enforce it before the first network call. This is the Tool Gateway's 12-stage pipeline. This is the capability manifest. This is `CapabilityViolationError`. Control is not a feature. It is a precondition.

---

> **"Observability precedes scale."**

You cannot improve what you cannot see. Every execution produces a `TraceContext`. Every step produces a `StepRecord` with hashed inputs and outputs. Calibrated confidence scores replace raw similarity metrics. `AgentStep` records persist to Azure SQL. Before you scale, you need to know exactly what is happening at every step of every execution. Observability is not monitoring. It is proof.

---

> **"Governance precedes automation."**

An automated system that acts without governance is a liability that scales. Meridian's confidence threshold, approval verification, separation of duties enforcement, and refusal path exist so that automation operates within defined boundaries — not despite them. Governance is not a brake on the system. It is what makes the system trustworthy enough to deploy.
