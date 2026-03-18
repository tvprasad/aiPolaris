# aiPolaris — System Boundary Document

**Classification:** For ATO authorization package
**Date:** 2026-03-15

## In Scope
- LangGraph agent DAG (Planner, Retriever, Synthesizer)
- AgentState schema and node ownership enforcement
- Tool manifest enforcement (CapabilityViolationError)
- TraceContext and StepRecord audit logging
- FastAPI API layer with streaming responses
- Entra ID authentication and RBAC middleware
- Azure AI Search retrieval (READ ONLY — does not own index)
- Session memory (conversation window, TTL=1800s)
- Prompt hash-pinning (prompts.lock)
- CI/CD security gates (SAST, dependency scan, secret detection)
- GCCH Terraform workspaces
- Immutable release records

## Out of Scope
- Data ingestion pipeline (owned by aiNexus)
- Document storage and chunking (owned by aiNexus)
- Graph API connector (owned by aiNexus)
- AI Search index population (owned by aiNexus)
- Persistent episodic memory across sessions (v2)
- UI layer (separate project)
- Human-in-the-loop approval workflow (v2)
- Model training or fine-tuning

## Data Flows
User query → FastAPI /query → Entra ID validation → RBAC check
→ AgentState init → LangGraph graph
→ Planner (no external calls)
→ Retriever (Azure AI Search READ only)
→ Synthesizer (state only, no external calls)
→ StreamingResponse → Session store update → Audit log write

## Boundary Note for ATO
aiPolaris reads the AI Search index owned by aiNexus.
It does not write to, populate, or manage that index.
The data boundary is the AI Search read endpoint.

## NIST 800-53 Key Controls
AC-2, AC-5, AC-6, AU-2, CM-3, CM-6,
IA-2, IA-5, IR-4, RA-3, SA-10, SA-11,
SC-4, SC-28, SI-2, SI-7, SI-10
