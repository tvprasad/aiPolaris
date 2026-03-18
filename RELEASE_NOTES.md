# Release Notes

Human-readable summary of each release.
Audience: strategy director, federal client reviewer, stakeholders.
Technical detail lives in CHANGELOG.md and release_records/.

---

## v0.1.0 — Initial scaffold (2026-03-15)

**What organizations get from this release:**
A production-grade agentic RAG scaffold that prevents the compliance debt
and ATO delays that derail most AI initiatives — federal or commercial.

**What's working:**
- Complete LangGraph agent graph: Planner → Retriever → Synthesizer
- Capability sandboxing enforced in code — CapabilityViolationError on any violation
- Full audit trail on every invocation — trace_id, StepRecord per node
- GCCH deployment path ready — one Terraform variable switches all endpoints
- CI/CD pipeline with 6 security gates — no manual compliance review required
- Eval harness seeded with 20 golden questions across 5 categories

**What's stubbed (Day 2 work):**
- Real Azure OpenAI LLM calls (nodes have stub implementations)
- Real Azure AI Search queries (Retriever returns empty until wired)
- Entra ID token validation (auth middleware stub — needs real MSAL implementation)
- Graph API connector (graph_api.py scaffold ready, needs credentials)

**Known gaps:**
- Session memory working, episodic memory deferred to v0.3
- Chunking strategy implemented, ADLS pipeline needs live Azure connection
- /ingest endpoint scaffolded, full pipeline wiring is Day 2

**Compliance posture:**
- System boundary document: docs/system-boundary.md
- NIST control mapping: docs/adr/ (each ADR maps to controls)
- ATO evidence: release_records/ (generated on every main merge)

---

## Release template

```
## v[X.Y.Z] — [date]

**What organizations get from this release:**
[One sentence in About You language — what problem this solves for them]

**What's new:**
- [Feature] — [why it matters to the operator/mission owner]
- [Security fix] — [what risk it eliminates]

**Eval delta:**
- p95 latency: [before] → [after]
- Incorrect refusal rate: [before] → [after]
- Follow-up pass rate: [before] → [after]

**Compliance additions:**
- [New control satisfied]: [how]
```
