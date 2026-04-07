# aiPolaris

[![CI](https://github.com/tvprasad/aiPolaris/actions/workflows/ci.yml/badge.svg)](https://github.com/tvprasad/aiPolaris/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](https://github.com/tvprasad/aiPolaris/releases/tag/v0.1.0)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-21_passing-brightgreen.svg)](tests/)
[![LangChain](https://img.shields.io/badge/LangChain-LCEL-blueviolet.svg)](agent/nodes/planner.py)
[![LangGraph](https://img.shields.io/badge/LangGraph-DAG-orange.svg)](agent/graph.py)
[![ADRs](https://img.shields.io/badge/ADRs-10-orange.svg)](docs/adr/)
[![GCCH](https://img.shields.io/badge/GCCH-ready-darkblue.svg)](infra/terraform/)

Federal AI agent orchestration stalls on compliance gaps, audit failures,
and capability boundaries that aren't enforced until production.
aiPolaris prevents that - from the first commit.

> *AI systems fail from architectural ambiguity, not model weakness.*

---

## What aiPolaris Is

The agent orchestration layer in the VPL Solutions AI platform.

| Product    | Role                                                  |
|------------|-------------------------------------------------------|
| Meridian   | Governed RAG control plane — retrieval + governance   |
| aiNexus    | Enterprise data pipeline — Graph API, ADLS, AI Search |
| **aiPolaris** | **Agent orchestration — LangGraph DAG, sandboxing, audit trail** |

aiPolaris reads the aiNexus index. It does not own or populate it.

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │         Entra ID Auth (MSAL)            │
                    │       RBAC per endpoint capability       │
                    └──────────────────┬──────────────────────┘
                                       │
                         POST /query (StreamingResponse)
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │           LangGraph DAG                  │
                    │                                          │
                    │  ┌──────────┐      ┌──────────────┐      │
                    │  │ Planner  │─────▶│  Retriever   │      │
                    │  │tools:none│      │tools:        │      │
                    │  └──────────┘      │ai_search_read│      │
                    │                    │only          │      │
                    │                    └──────┬───────┘      │
                    │                           │              │
                    │                ┌──────────▼──────────┐   │
                    │                │    Synthesizer      │   │
                    │                │    tools: none      │   │
                    │                │  answer + citations │   │
                    │                └─────────────────────┘   │
                    │                                          │
                    │  TraceContext: trace_id + StepLog        │
                    │  CapabilityViolationError enforced       │
                    │  Session memory: TTL=1800s               │
                    └──────────────────────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │  Azure AI Search (READ ONLY)            │
                    │  Index owned by aiNexus                 │
                    │  Confidence threshold: 0.75             │
                    └──────────────────────────────────────────┘

GCCH: set environment=gcch in Terraform workspace.
All endpoints switch automatically. Zero code changes.
```

---

## Key Properties

**Deterministic** — temperature=0, pinned model, pinned prompts (prompts.lock).
Same input → same output. Verifiable from trace_id alone.

**Sandboxed** — every agent node has a declared tool manifest.
CapabilityViolationError raised immediately on any violation. Tested.

**Auditable** — every invocation has a trace_id. Every node appends a StepRecord.
Full execution reconstructable from the audit log. Satisfies NIST AU-2, IR-4.

**GCCH-ready** — all endpoints parameterized by Terraform workspace variable.
Commercial → GCCH is one command.

---

## Eval Acceptance Criteria

| Metric                  | Threshold     |
|-------------------------|---------------|
| p95 latency             | < 4,000 ms    |
| p50 latency             | < 1,500 ms    |
| Avg confidence          | > 0.75        |
| Correct refusal rate    | 100%          |
| Incorrect refusal rate  | < 10%         |
| Follow-up pass rate     | 4/4 (100%)    |
| Sandbox tests           | 100% pass     |
| Replay match rate       | ≥ 95%         |

---

## Getting Started

```bash
make install       # pip install -e .[dev] + pre-commit hooks
make dev           # uvicorn on port 8000
make graph-viz     # export LangGraph DAG as Mermaid
make eval          # run full eval harness (20 questions)
make tf-plan env=commercial
make tf-plan env=gcch
```

---

## ADRs

| ADR     | Decision                                       |
|---------|------------------------------------------------|
| ADR-001 | LangGraph over LangChain / SK / AutoGen        |
| ADR-002 | Read-only agents, CapabilityViolationError     |
| ADR-003 | GCCH Terraform workspaces                      |
| ADR-004 | TraceContext on every invocation               |
| ADR-005 | Prompt hash-pinning via prompts.lock           |
| ADR-006 | Streaming responses                            |
| ADR-007 | Session memory (TTL=1800s)                     |

---

## Philosophy

Control precedes generation. Observability precedes scale.
Governance precedes automation.

I design systems where failure modes are explicit, not discovered in production.

---

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://linkedin.com/in/tvprasad)
[![GitHub](https://img.shields.io/badge/GitHub-tvprasad-181717?style=flat&logo=github)](https://github.com/tvprasad)
