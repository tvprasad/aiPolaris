# aiPolaris — Q&A Review Document
### Internal Use Only · VPL Solutions LLC

---

## The Agent & Orchestration

---

**1. What is the agent? What makes it an agent and not just a function?**

A function takes an input, does one thing, and returns an output. It has no memory of what happened before, no awareness of intermediate steps, and no ability to decide what to do next based on what it found.

An agent does more. It receives a goal, breaks it into steps, executes each step using tools or reasoning, carries results forward through shared state, and produces a final answer that depends on what every prior step discovered.

In aiPolaris, the agent is the entire Planner → Retriever → Synthesizer pipeline. What makes it an agent:
- It decomposes a question before answering it
- It uses a real tool (Azure AI Search) to gather evidence
- Each step sees what the prior step produced
- It can refuse — returning a structured non-answer when evidence is insufficient
- Every execution is logged with enough detail to replay it identically

A function cannot do any of that.

---

**2. What orchestrates? What is being orchestrated?**

**LangGraph** does the orchestrating.

It is a framework that runs a stateful, directed graph — controlling which node runs next, what data each node receives, and when execution ends. The wiring is declared once in `agent/graph.py`:

```
Planner → Retriever → Synthesizer → END
```

What is being orchestrated: **two Azure OpenAI calls and one Azure AI Search call** — in a fixed sequence, with shared state passed between them.

- Planner: Azure OpenAI GPT-4o — breaks the question apart
- Retriever: Azure AI Search — fetches evidence
- Synthesizer: Azure OpenAI GPT-4o — writes the answer from evidence

LangGraph handles routing, state threading, and execution flow. Your code only defines what each node does — not how they connect.

---

**3. What holds state? What is the state?**

`AgentState` holds state. It is a Python `TypedDict` — a typed dictionary passed through every node in the graph.

What is in it:

```
query              ← the original question, sealed at entry
session_context    ← prior Q&A from this user's session (if any)
user_oid           ← identity of the caller, from the auth token
sub_tasks          ← written by Planner only
retrieved_chunks   ← written by Retriever only
answer             ← written by Synthesizer only
citations          ← written by Synthesizer only
trace              ← every node appends a record here, nobody replaces it
```

The state is the single source of truth for the entire execution. Nodes do not call each other. They read from state, write their own slice, and return. LangGraph routes the updated state to the next node.

---

## The DAG Nodes

---

**4. What does the Planner own? What can it never touch?**

The Planner owns one field: `sub_tasks`.

It reads the incoming question and — if available — the prior conversation context from the session. It calls GPT-4o to break the question into a list of specific retrieval queries. It writes that list into `sub_tasks` and returns.

It can never touch: Azure AI Search, ADLS, Key Vault, Graph API, or any other data source. It has no tool access at all. Its manifest declares an empty allowed tools list. Any attempt to call an external tool raises a `CapabilityViolationError` immediately.

The Planner reasons. It does not retrieve.

---

**5. What does the Retriever own? What is it never allowed to call?**

The Retriever owns one field: `retrieved_chunks`.

It reads `sub_tasks` from the Planner, executes hybrid semantic search against Azure AI Search for each sub-task, filters out low-confidence results, deduplicates by source document, and writes the surviving chunks into `retrieved_chunks`.

It is never allowed to call anything outside its manifest. Its only permitted tool is `ai_search_read` — a read operation against the search index. Any write operation, any Graph API call, any credential access — all raise `CapabilityViolationError` before the network is reached.

The Retriever fetches. It does not reason. It does not write.

---

**6. What does the Synthesizer own? What does it refuse to do when it has nothing?**

The Synthesizer owns two fields: `answer` and `citations`.

It reads `retrieved_chunks` from the Retriever, along with the original question and session context. It calls GPT-4o to compose a grounded answer from the chunks and extract citations. It writes both into state.

When `retrieved_chunks` is empty — meaning the Retriever found nothing above the confidence threshold — the Synthesizer does not call GPT-4o. It returns a hardcoded refusal string immediately:

> *"I don't have enough information in my knowledge base to answer this question accurately."*

This string is not generated. It is not inferred. It is a constant in the code. There is no path to a hallucinated answer.

---

## Capability & Safety

---

**7. What enforces capability? What happens the moment it is violated?**

`check_capability()` enforces capability. It is called in code, before every tool invocation — before any network call is made.

It compares the requested tool name against the node's declared manifest (its allowed tools list). If the tool is not in the list, it raises `CapabilityViolationError` immediately. The Azure SDK is never reached. No request leaves the application.

This is a security control, not a runtime convenience. A bug, a misconfigured node, or a malicious prompt injection cannot cause a write operation — because the enforcement happens in Python before any external call.

---

**8. What is a manifest? Who declares it, and when is it checked?**

A manifest is a declaration of what tools a node is allowed to use. It is defined at module level in `agent/tools/manifests.py` — once per node, at import time, before any request is handled.

Each manifest contains:
- The node's name
- The list of allowed tool names (can be empty)
- The reason all other tools are denied

The check happens inside the node itself, at the exact line where a tool would be called. Not at the graph level. Not in middleware. At the call site — so there is no way to call a tool without passing through the check.

---

**9. What is the confidence gate? What gets through, what doesn't, and why?**

The confidence gate is a reranker score threshold in the Retriever. Azure AI Search returns a semantic reranker score between 0 and 4 for every result. aiPolaris sets a minimum of **0.60**.

Any chunk with a score below 0.60 is dropped before it reaches the Synthesizer. It never appears in the answer. It is never cited.

Why 0.60: chunks below this threshold are semantically distant from the query. Including them would give the Synthesizer weak or irrelevant evidence — which either degrades the answer quality or forces the model to fabricate connections that aren't there. The gate prevents both outcomes by simply withholding the evidence.

If nothing survives the gate, the Synthesizer returns a structured refusal. Correct refusal rate: 100% on out-of-scope questions.

---

## Identity & Access

---

**10. What checks identity? What four things does it verify every time?**

The auth middleware checks identity. It runs on every request before any route handler or node executes.

It validates the Entra ID bearer token on four dimensions — every time, no exceptions:

1. **Signature** — was this token issued and signed by a trusted authority?
2. **Expiry** — has this token expired?
3. **Audience** — was this token issued for this application specifically?
4. **Issuer** — did it come from the expected Entra ID tenant?

A token that passes all four is accepted. A token that fails any one is rejected with 401 before the request proceeds.

---

**11. What does identity unlock? What does role determine?**

Identity unlocks access to the system. Role determines what you can do inside it.

Once the token is validated, the RBAC middleware reads the `roles` claim from the token payload. Roles map to capabilities:

| Role | Capabilities |
|---|---|
| `user` | query |
| `operator` | query, ingest, settings |
| `admin` | query, ingest, settings, eval, audit |

A user role can ask questions. An operator role can also trigger ingestion. An admin can also run evaluations and access audit records. The mapping is declared in code — not in a policy document.

---

**12. What is RBAC? Where does it live — and where is it forbidden to live?**

RBAC stands for Role-Based Access Control. It is the rule that determines whether a given user is allowed to perform a given action.

In aiPolaris it lives exclusively in middleware — `api/middleware/rbac.py`. Every route that requires a capability declares it as a FastAPI dependency: `Depends(require_capability("ingest"))`. The check runs before the route handler executes.

It is forbidden inside route handlers. This is a deliberate constraint. Route handlers are where business logic lives. If RBAC checks were scattered through route handlers, one missed check would be a security gap. Centralizing in middleware means every route either has the dependency or it doesn't — there is no "almost protected" state.

---

## Trace & Audit

---

**13. What writes the trace? What is in each record?**

Every node writes to the trace — automatically, before returning. No node can skip it.

Each record (`StepRecord`) contains:

| Field | What It Captures |
|---|---|
| `node_name` | Which node produced this record |
| `input_hash` | SHA-256 fingerprint of what the node received |
| `tool_calls` | Names of every tool actually called (empty list if none) |
| `output_hash` | SHA-256 fingerprint of what the node produced |
| `latency_ms` | How long the node took to execute |
| `timestamp` | UTC ISO 8601 timestamp |

All three records from a single execution are bundled under one `trace_id`. That ID travels in the HTTP response header so the caller can reference it immediately.

---

**14. What is a `trace_id`? Who uses it after the query is done?**

`trace_id` is a UUID generated fresh at the start of every graph invocation. It is the single identifier that ties every log entry, every step record, and every audit artifact from one execution back together.

Who uses it after the query is done:

- **Compliance officers** — to look up the full execution and verify what sources were used
- **Developers** — to diagnose a specific invocation that produced a wrong or unexpected answer
- **The eval harness** — to replay an execution and verify it produces identical output
- **The audit trail** — to reconstruct the exact sequence of steps for any historical query

It is returned in the HTTP response header `X-Trace-Id` so the caller has it immediately.

---

**15. What makes an execution replayable? What three things must be pinned?**

Replayability means: given the same inputs, you get the same output — identically, every time.

Three things must be pinned:

1. **The model** — Azure OpenAI GPT-4o. The same deployment, same version.
2. **The prompts** — system instructions to the model, hash-locked in `prompts.lock`. Any change to a prompt file changes its SHA-256 fingerprint and breaks the lock check.
3. **The temperature** — set to 0. Temperature controls randomness. At 0, the model is deterministic. At any higher value, the same prompt produces a different token sequence on each run.

Without all three pinned, the same `trace_id` could produce a different answer tomorrow than it did today. The replay match rate target is ≥ 95%.

---

## Prompts

---

**16. What pins the prompts? What breaks if a prompt changes without a record?**

`prompts.lock` pins the prompts. It stores the SHA-256 fingerprint of every system prompt file. When a prompt file changes, its fingerprint changes. The CI pipeline runs `scripts/check_prompts.py` on every build — if any fingerprint in `prompts.lock` does not match the current file, the build fails.

What breaks: the build. The change cannot be merged. No deployment can happen until the lock file is updated — which requires a deliberate, recorded decision.

This means no prompt can silently drift. Every change is explicit, traceable, and tied to a commit.

---

**17. What is `prompts.lock`? What triggers a CI failure?**

`prompts.lock` is a file that records the SHA-256 hash of every prompt file in the system. It is the source of truth for what the model is being told to do.

A CI failure is triggered when any prompt file's current hash does not match the hash recorded in `prompts.lock`. This happens when:
- A prompt file was edited without updating the lock
- A prompt file was deleted
- A new prompt file was added without being registered

The fix is always the same: run the update script, review the diff, commit the updated lock alongside the prompt change with a clear explanation of why.

---

## Memory

---

**18. What scopes the memory? What forgets, and when?**

`InMemorySessionStore` scopes the memory. It is keyed by `session_id` — a UUID that identifies one conversation window.

The store forgets automatically. Every entry has a TTL of 1800 seconds (30 minutes). On every `.get()` call, the store checks how long ago the session was last accessed. If it has been more than 30 minutes, the entry is deleted and `None` is returned — as if the session never existed.

There is no manual cleanup required. Inactivity is the expiry trigger.

---

**19. What is a `session_id`? What does it prevent?**

`session_id` is a UUID that identifies one user's conversation window. It is either provided by the client or generated fresh on the first request.

It prevents two things:

1. **False refusals on follow-up questions** — without session context, a follow-up like "what about IR-4 specifically?" has no anchor. The Planner sees it as a standalone question and may decompose it incorrectly, leading to poor retrieval and a refusal. With session context, the prior question and answer are passed into the Planner, giving it the context to decompose correctly.

2. **Cross-session leakage** — each `session_id` is isolated. One user's prior Q&A cannot appear in another user's session. TTL expiry ensures that even within one session, context does not persist indefinitely.

---

## Ingestion Pipeline

---

**20. What pulls the documents? From where, with what permissions?**

`GraphAPIConnector` pulls the documents from SharePoint via the Microsoft Graph API.

It authenticates using managed identity — no API keys, no passwords. The credential is fetched from Azure Key Vault at runtime by the application's user-assigned identity.

Permissions are scoped to read-only at the Graph API level:
- `Sites.Read.All` — list SharePoint sites
- `Files.Read.All` — download document content

No write scope is requested. No write scope is granted. Any attempt to call a write operation is a capability violation.

---

**21. What stages the documents? Where do they land before the index?**

ADLS Gen2 (Azure Data Lake Storage) stages the documents. After the Graph API connector pulls a document from SharePoint, it writes the raw content to ADLS under a path structured by `site_id` and `pull_id`.

The `raw/` container is the landing zone. Documents sit here before chunking and indexing. This two-step design (pull → stage → index) means:
- The raw document is preserved independently of the index
- Reprocessing is possible without re-pulling from SharePoint
- Each pull is traceable by `pull_id`

---

**22. What chunks the documents? What problem does chunking solve?**

`OverlappingWindowChunker` chunks the documents. It splits each document into segments of approximately 512 tokens.

The problem chunking solves: language models have a fixed context window. A full document — often thousands of words — does not fit. More importantly, the model should reason over the most relevant passages, not an entire document. Chunking breaks the document into pieces small enough for the model to reason about precisely, while large enough to contain complete thoughts.

Target: 512 tokens per chunk. Minimum: 100 tokens. Maximum: 600 tokens. Chunks shorter than the minimum are merged into the previous chunk rather than discarded.

---

**23. What is overlap? Why does a chunk need to carry context from the one before it?**

Overlap is a deliberate repetition of content between adjacent chunks. In aiPolaris, each chunk carries approximately 10% of the previous chunk's content at its start (~51 tokens).

Why: document meaning does not stop at a chunk boundary. A sentence can begin in one chunk and conclude its meaning in the next. Without overlap, a chunk that starts mid-thought is missing the context that makes it interpretable.

With 10% overlap, the end of chunk N appears at the beginning of chunk N+1. The Retriever can return either chunk and the Synthesizer will have enough context to reason about it correctly.

---

## The Index

---

**24. What owns the index? What only reads it?**

**aiNexus owns the index.** It is responsible for pulling documents from SharePoint, staging them in ADLS, chunking them, and writing chunks into Azure AI Search. aiNexus creates and maintains the index.

**aiPolaris only reads it.** It submits search queries and receives results. It has no write access to the index, no ability to create or delete documents, and no visibility into how the index was built. If the index changes, aiPolaris sees updated results automatically — without any code change.

This boundary is intentional. Data ownership and query execution are separate responsibilities.

---

**25. What is a reranker score? What happens to a chunk that scores below 0.60?**

Azure AI Search runs a two-stage retrieval process. The first stage retrieves candidate chunks by keyword and vector similarity. The second stage — semantic reranking — re-scores each candidate on how well it actually answers the query, not just how well it matches keywords.

The reranker score is this second-stage score. It ranges from 0 to 4. A score close to 4 means the chunk is directly and precisely relevant to the query. A score below 0.60 means the chunk is a weak or incidental match.

Any chunk scoring below 0.60 is dropped by the Retriever before the results are passed to the Synthesizer. It does not appear in the answer. It is not cited. If all chunks fall below the threshold, the Synthesizer returns a structured refusal.

---

## Streaming

---

**26. What streams the response? What is actually in each SSE event?**

FastAPI's `StreamingResponse` streams the response over Server-Sent Events (SSE). The connection stays open after the graph finishes executing, and the answer is sent in chunks of 20 characters at a time.

Each SSE event is a JSON object. There are two types:

```json
// During answer delivery:
{ "type": "token", "content": "The FedRAMP High incident re" }

// On completion:
{ "type": "done", "citations": [...], "trace_id": "...", "latency_ms": 1855.4 }
```

The `done` event carries everything the client needs beyond the answer text: citations for the source panel, the `trace_id` for audit reference, and the total latency.

---

**27. What does the client receive at the end of a stream — beyond the answer?**

At the end of the stream, the client receives a `done` event containing:

- **Citations** — the source documents the answer was grounded in, with title, source path, and last modified date
- **`trace_id`** — the unique identifier for this execution, for audit and replay
- **`latency_ms`** — total wall-clock time from request to completion

Additionally, the HTTP response headers carry `X-Session-Id` and `X-Trace-Id` from the moment the response opens — so the client has the trace reference before the first token arrives.

---

## Infrastructure

---

**28. What runs the application? Where does it live in Azure?**

The application runs as an **Azure Container App** — a managed container hosting service that handles scaling, networking, and deployment without requiring the team to manage Kubernetes directly.

It scales between 0 and 3 replicas automatically based on traffic. At zero traffic, it scales to zero (no cost). It exposes one public HTTPS endpoint. It is connected to a Log Analytics workspace for all operational logs.

The container image is pulled from Azure Container Registry — the same registry shared with Meridian.

---

**29. What stores the secrets? How does the application get them at runtime?**

**Azure Key Vault** stores all secrets — API keys, client secrets, connection strings. Nothing sensitive is stored in code, environment variable files, or container image layers.

At runtime, the application authenticates to Key Vault using its **user-assigned managed identity** — a certificate-based credential that Azure manages automatically. The application never handles a password. It presents its identity to Azure, Azure verifies it, and Key Vault returns the secret value for that session.

This means: no secret rotation in code, no credentials to rotate manually, no risk of a credential leaking through a log file or environment dump.

---

**30. What switches the environment? What changes between commercial and GCCH — and what never changes?**

**Terraform** switches the environment. A single variable — `var.environment` — is set to either `commercial` or `gcch`. Terraform resolves all endpoints from that one value in `settings.tf`.

What changes between commercial and GCCH:

| Service | Commercial | GCCH |
|---|---|---|
| Azure OpenAI | `*.openai.azure.com` | `*.openai.azure.us` |
| Azure AI Search | `*.search.windows.net` | `*.search.azure.us` |
| Microsoft Graph | `graph.microsoft.com` | `graph.microsoft.us` |
| ADLS Gen2 | `*.dfs.core.windows.net` | `*.dfs.core.usgovcloudapi.net` |
| Key Vault | `*.vault.azure.net` | `*.vault.usgovcloudapi.net` |
| Entra ID | `login.microsoftonline.com` | `login.microsoftonline.us` |

What never changes: the application code. Every endpoint is injected as an environment variable at deploy time. No URL appears in Python source files.

---

**31. What is managed identity? What problem does it eliminate?**

Managed identity is an Azure-native credential that lives on a resource — not in a config file or a developer's laptop. Azure creates it, rotates it, and manages its lifecycle automatically.

The problem it eliminates: **credential management**. Without managed identity, every service-to-service call requires an API key or client secret — a string that must be:
- Generated and stored somewhere
- Rotated periodically
- Never accidentally committed to source control
- Never appear in logs

Managed identity removes all of that. The application presents its identity to Azure. Azure verifies it. The target service grants access based on that identity, not a password. No string ever exists that could be leaked.

---

## The Bigger Picture

---

**32. What does aiPolaris not own? What does it depend on that it did not build?**

aiPolaris does not own:

- **The knowledge index** — Azure AI Search is populated and maintained by aiNexus. aiPolaris only queries it.
- **The documents** — SharePoint content belongs to the organization. aiPolaris reads it through the Graph API but does not store or govern it.
- **The container registry** — shared with Meridian. aiPolaris pushes to it but does not own the infrastructure.
- **The governance and evaluation layer** — Meridian owns confidence gating, citation UI, and eval scoring at the product level. aiPolaris produces the raw answer and citations; Meridian decides what to do with them.

What aiPolaris owns: the orchestration layer — the DAG, the agent nodes, the capability enforcement, the trace, the session memory, and the API surface.

---

**33. What is the relationship between aiPolaris, aiNexus, and Meridian?**

Three distinct systems, each owning a different layer:

```
aiNexus
  Owns the data pipeline.
  Pulls documents from SharePoint via Graph API.
  Stages them in ADLS Gen2.
  Chunks and indexes them into Azure AI Search.
  → Produces the knowledge index.

aiPolaris
  Owns the orchestration layer.
  Reads the aiNexus index.
  Runs the Planner → Retriever → Synthesizer DAG.
  Enforces capability boundaries and trace.
  → Produces a grounded, cited, traceable answer.

Meridian
  Owns the governance layer.
  Confidence-gates retrieval quality.
  Provides the MCP tool server for Claude Desktop.
  Surfaces the citation panel and audit trail UI.
  → Governs what answers reach end users and how.
```

aiPolaris is the middle layer. It depends on aiNexus for content and feeds Meridian with answers.

---

**34. What would break first if the index went down? What would still work?**

**What breaks first:** the Retriever. It queries Azure AI Search on every execution. With the index down, it returns an empty chunk list. The Synthesizer receives nothing and returns a structured refusal for every query.

**What still works:**
- Authentication and RBAC — fully independent of the index
- The Planner — it calls Azure OpenAI to decompose the query, which has nothing to do with the index
- Session memory — reads and writes from the in-memory store, no index dependency
- The trace — every node still appends its `StepRecord`, including the refusal path
- The streaming response — the refusal answer is still delivered over SSE with a `trace_id`
- The ingestion endpoint — pulling and staging documents does not depend on the query index being live

The system degrades gracefully. It does not crash. It refuses every query with a consistent, logged, traceable response — and resumes normal operation the moment the index is restored.
