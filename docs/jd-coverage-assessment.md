# AI Platform Engineer — JD Coverage Assessment
### Internal Use Only · VPL Solutions LLC
### Covers: aiPolaris + Meridian combined

---

## Must Have

---

### Python
**Status: Fully covered — both projects**

Python 3.12 across the board. FastAPI async handlers, Pydantic v2 models, SQLAlchemy 2.x ORM, dataclasses, TypedDict, abstract base classes, generators, context managers, threading locks.

- aiPolaris: `agent/`, `api/`, `pipeline/` — async FastAPI, LangGraph nodes, Azure SDK integration
- Meridian: `services/`, `core/`, `tool_gateway/`, `ops_copilot/` — 525+ tests, 12-stage pipeline, ReAct agent loop

---

### LLM SDKs — OpenAI
**Status: Fully covered — both projects**

`openai` SDK used directly in both projects.

- aiPolaris: `AsyncAzureOpenAI` — async streaming calls in Planner and Synthesizer nodes
- Meridian: `AzureOpenAI` — sync and streaming generation in `AzureOpenAIProvider`, function calling in the ReAct agent executor (`tool_choice="auto"`, `tools=TOOL_DEFINITIONS`)

Both projects set `temperature`, `max_tokens`, and use structured response formats.

---

### LLM SDKs — Anthropic
**Status: Covered via MCP integration — Meridian**

Meridian's MCP server (`server_mcp/`) exposes the RAG control plane to Claude Desktop. The `integrations/claude_desktop_config.example.json` configures the Anthropic toolchain. The system is designed to be model-agnostic — `providers/base.py` defines an abstract `LLMProvider` interface with `generate()` and `generate_stream()` that any provider implements. Ollama, Azure OpenAI, and Claude (via MCP) are all supported.

Direct `anthropic` SDK usage is through MCP rather than the Python client — which is the production pattern for Claude Desktop integration.

---

### Vector Database
**Status: Fully covered — Meridian (ChromaDB + Azure AI Search)**

Meridian runs two vector stores in parallel:

**ChromaDB** (`services/retrieval/chroma_store.py`):
- Persistent local vector store
- Embedding model: `all-MiniLM-L6-v2` via `SentenceTransformerEmbeddingFunction`
- Lazy, thread-safe initialization with double-checked locking
- `add_document()` — store and embed
- `query_documents()` — top-K semantic retrieval
- Configured via `settings.CHROMA_PATH`, `settings.CHROMA_COLLECTION`, `settings.TOP_K`

**Azure AI Search** (`services/retrieval/azure_search_adapter.py`):
- Cloud-scale vector + keyword hybrid search
- Semantic reranker scoring
- Production retrieval backend

The retrieval layer abstracts both behind `services/retrieval/base.py` — the control plane does not care which store answers the query.

aiPolaris uses Azure AI Search exclusively (owned by aiNexus).

---

### OpenSearch
**Status: Not directly present — covered by equivalent**

Neither project uses OpenSearch. Both use Azure AI Search, which is the enterprise-managed equivalent — vector search, BM25 keyword search, semantic reranking, index management. The operational and conceptual skills are directly transferable.

This is a gap worth stating clearly: OpenSearch is open-source (Elasticsearch fork), Azure AI Search is managed PaaS. The retrieval engineering patterns are identical; the operational tooling differs.

---

### Embedding Pipelines
**Status: Covered — Meridian**

Meridian runs a full embedding pipeline:

- **Model**: `all-MiniLM-L6-v2` via `sentence-transformers`/PyTorch
- **Framework**: ChromaDB `SentenceTransformerEmbeddingFunction` — handles tokenization, inference, and vector storage in one call
- **Chunking**: `OverlappingWindowChunker` in aiPolaris (`pipeline/chunking/strategy.py`) — 512-token target, 10% overlap, sentence-boundary alignment, min/max token enforcement, metadata preservation per chunk
- **Ingestion**: `services/ingestion/` — file upload and ServiceNow KB connector feed documents into the embedding pipeline

The full pipeline is: raw document → chunk → embed → store → query → rerank → retrieve.

---

### Prompt Chaining Frameworks
**Status: Fully covered — both projects**

**aiPolaris**: LangGraph — a stateful DAG framework for chaining agent nodes. Each node is a step in the chain. State flows between nodes. The chain is: Planner → Retriever → Synthesizer.

**Meridian**: ReAct loop in `services/agent/executor.py` — a multi-step reasoning chain where the LLM selects a tool, the tool executes, the result is fed back into the next LLM call, and the loop continues until the LLM produces a final answer or the step budget is exhausted. This is prompt chaining at the agentic level.

Both patterns — DAG-based chaining and ReAct loop chaining — are represented and production-deployed.

---

### LangChain
**Status: Not directly used — covered by LangGraph**

LangGraph is built and maintained by LangChain Inc. — it is the stateful, graph-based evolution of LangChain's agent architecture. aiPolaris uses LangGraph directly.

LangChain (the original framework) is not imported. The distinction: LangChain provides chains, agents, and memory abstractions; LangGraph provides explicit stateful DAGs with typed state ownership. For production agentic systems, LangGraph supersedes LangChain's agent patterns.

This is a gap worth noting in a technical conversation — not a capability gap, but a framework vocabulary gap.

---

### LlamaIndex
**Status: Not present**

LlamaIndex is not used in either project. The retrieval and ingestion patterns it addresses (document loading, chunking, indexing, query engines) are implemented directly:

- Document loading: Graph API connector (`pipeline/connectors/graph_api.py`), ServiceNow KB connector
- Chunking: `OverlappingWindowChunker`
- Indexing: Azure AI Search adapter, ChromaDB store
- Query engine: Retriever node (aiPolaris), Azure Search + Chroma adapters (Meridian)

The functionality is present; LlamaIndex as an abstraction layer is not. This is a genuine gap if the role specifically requires LlamaIndex API experience.

---

## Must Understand

---

### Token Cost Optimization
**Status: Covered — both projects**

Multiple cost-control mechanisms in production:

- `temperature=0` — eliminates sampling overhead, reduces retry costs from non-determinism
- `max_tokens` — hard ceiling on output length, both projects
- 512-token chunking — keeps context windows tight; only relevant chunks reach the LLM
- Top-K retrieval (K=5) — limits context size passed to Synthesizer
- Step budget in ReAct agent (default: 5 steps) — caps LLM calls per query
- Agent deadline (`settings.AGENT_TIMEOUT_S`) — wall-clock limit regardless of steps
- Refusal path on empty retrieval — skips LLM call entirely when no evidence exists

These are not theoretical optimizations. They are enforced in code on every request.

---

### Streaming Interface
**Status: Fully covered — both projects**

**aiPolaris**: FastAPI `StreamingResponse` + SSE. Token-by-token delivery in `api/routers/query.py`. Each SSE event is a typed JSON object (`token`, `done`, `error`). The `done` event carries citations, `trace_id`, and `latency_ms`. Response headers include `X-Trace-Id` from the moment the connection opens.

**Meridian**: `generate_stream()` on `LLMProvider` base class. `AzureOpenAIProvider` implements native streaming (`stream=True`) — yields token chunks directly from the Azure OpenAI response. `OllamaProvider` implements line-by-line streaming from the Ollama HTTP endpoint.

Both sync and async streaming patterns are implemented.

---

### Retry / Fallback Models
**Status: Partially covered — mechanism exists, not fully built out**

**What exists:**
- Planner falls back to `[query]` on JSON parse error — never raises to caller
- Synthesizer returns a hardcoded refusal string on empty retrieval — never calls LLM blindly
- `OllamaProvider` raises typed errors (`RuntimeError`) with actionable retry messages on `ConnectionError` and `Timeout`
- `LLMProvider.generate_stream()` defaults to `generate()` if streaming is not overridden — a built-in fallback
- Tool Gateway rate limiting returns `retryable=True` with `retry_after_s` in the error payload

**What is not present:**
- Explicit retry with exponential backoff on Azure OpenAI transient errors
- Automatic failover from Azure OpenAI to Ollama on provider failure
- Circuit breaker pattern

The architecture supports provider swapping (the abstract `LLMProvider` makes it possible to add a fallback provider), but the automatic retry/failover logic is not wired up. This is an honest gap.

---

### Function Calling / Tool Use
**Status: Fully covered — both projects, at depth**

**aiPolaris**: Manifest-enforced tool use. `CapabilityViolationError` raised before any out-of-manifest tool call. Every node's allowed tools are declared at module load time. Tool calls are recorded in `StepRecord.tool_calls` for audit.

**Meridian — ReAct Agent**: Native OpenAI function calling (`tools=TOOL_DEFINITIONS`, `tool_choice="auto"`). The LLM selects tool and arguments. Arguments are parsed from JSON. Tool executes. Result fed back to LLM. This is the standard function calling pattern from the OpenAI API.

**Meridian — Tool Gateway**: A 12-stage enforcement pipeline that governs every tool execution:
- Stage 2: Token validation
- Stage 3: Agent registration check
- Stage 4: Manifest check (capability sandboxing)
- Stage 5: Boundary enforcement (research = read-only, exec = write-only)
- Stage 6: Input schema validation (Pydantic)
- Stage 7: SQL query safety check (DDL/DML/injection prevention)
- Stage 8: Approval verification for write tools (separation of duties, plan hash integrity, scope match)
- Stage 9: Rate limiting per agent

This is not a toy tool use example. It is a production governance layer over agentic tool execution.

---

## Core Responsibilities

---

### LLM Integration
**Status: Fully covered**

- Python 3.12 throughout
- `openai` SDK: async (aiPolaris) and sync (Meridian) usage, streaming in both
- Azure OpenAI: managed identity + API key auth, deployment configuration, versioned API calls
- Ollama: local inference provider for development
- Claude via MCP: production integration with Anthropic toolchain
- Abstract provider pattern: model-agnostic control plane in Meridian

---

### Search & Retrieval
**Status: Fully covered**

- **Azure AI Search**: hybrid semantic search, reranker scoring, confidence gating, top-K filtering, deduplication by source (both projects)
- **ChromaDB**: persistent vector store, SentenceTransformer embeddings, similarity search (Meridian)
- **Embedding pipeline**: all-MiniLM-L6-v2, chunking strategy with overlap, metadata preservation (Meridian + aiPolaris pipeline)
- **Calibrated confidence scoring**: isotonic regression calibrator maps raw L2-distance similarity scores to calibrated probabilities — `CalibratedScorer` in Meridian

---

### Orchestration
**Status: Fully covered — two distinct patterns**

- **LangGraph DAG** (aiPolaris): stateful, typed, deterministic. Fixed sequence with explicit state ownership per node.
- **ReAct loop** (Meridian): dynamic, multi-step, tool-driven. LLM decides what to call next based on prior tool results.

Together these cover the two dominant agentic orchestration patterns. LangChain and LlamaIndex are not used by name, but the orchestration capabilities they provide are present.

---

### System Reliability
**Status: Covered with one gap**

**Present:**
- Graceful degradation: empty retrieval → structured refusal, never a crash
- Step budget + deadline: agent cannot run indefinitely
- Rate limiting per agent with `retry_after_s`
- Typed error pipeline: every failure has an `ErrorType`, HTTP status, and structured details
- Health endpoint: `/health` for liveness and readiness probes
- Container App scaling: 0–3 replicas with liveness/readiness probes in Terraform

**Gap:**
- No automatic retry with backoff on Azure OpenAI transient errors
- No failover to secondary LLM provider

---

### Feature Development — Streaming + Function Calling
**Status: Fully covered**

Both features are production-implemented, not prototyped:
- Streaming: SSE with typed events, citations on completion, trace ID in headers
- Function calling: native OpenAI tool use in ReAct agent + 12-stage governed tool execution in Tool Gateway

---

## Summary

| Requirement | Status |
|---|---|
| Python | Fully covered |
| OpenAI SDK | Fully covered |
| Anthropic SDK | Covered via MCP (Claude Desktop integration) |
| Vector DB | Fully covered — ChromaDB + Azure AI Search |
| OpenSearch | Not present — Azure AI Search is the production equivalent |
| Embedding pipelines | Covered — SentenceTransformer, chunking strategy, ingestion pipeline |
| Prompt chaining frameworks | Fully covered — LangGraph DAG + ReAct loop |
| LangChain | Not directly used — LangGraph (same org, successor pattern) |
| LlamaIndex | Not present — equivalent functionality built directly |
| Token cost optimization | Covered — temperature=0, max_tokens, top-K, step budget, refusal path |
| Streaming interface | Fully covered — SSE + native provider streaming |
| Retry / fallback models | Partial — fallback paths exist, automatic retry not wired up |
| Function calling / tool use | Fully covered — native OpenAI tool use + 12-stage Tool Gateway |

### Three gaps to address directly in any technical conversation:
1. **OpenSearch** — use Azure AI Search as the equivalent; explain the operational trade-offs
2. **LangChain / LlamaIndex** — use LangGraph as the successor; explain why it was chosen over LangChain agents
3. **Retry / fallback** — the architecture supports it; the automatic wiring is not complete
