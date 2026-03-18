# AI Delivery Process

**Audience:** Strategy director, federal client reviewer, new team member
**Purpose:** Documents how every engagement runs — intake through release

---

## The problem this process solves

Federal AI initiatives stall on compliance debt, ATO delays, and security
retrofits done too late. This process prevents that by generating compliance
evidence as a byproduct of building — not as a separate effort afterward.

---

## The five-phase loop

Every engagement — a portfolio project, a federal contract, an internal
tool — runs the same loop. Only the compliance framework and data sensitivity
tier change between engagements.

### Phase I — Intake
**Who:** Prasad (human judgment required — cannot be delegated)
**What:** Client conversation → bullet-point inputs → Claude generates 6 artifacts simultaneously

Artifacts produced:
- Use case document (3–5 use cases, acceptance criteria per use case)
- System boundary statement (in-scope, out-of-scope, data flows)
- Threat model (capability boundaries, permission tiers, data sensitivity)
- Eval acceptance criteria (metric thresholds, golden question categories)
- CLAUDE.md draft (ADR constraints, stack, never-do rules)
- ADR briefs for each architectural decision

**Intake prompt:** See docs/process/intake-prompt.md

### Phase II — Parallel execution
**Who:** Claude Code (all tracks simultaneously)
**What:** Code, infrastructure, security gates — all tracks run in parallel

- Track A (ML Engineer): AgentState → node stubs → LangGraph DAG → eval harness
- Track B (Data Engineer): connectors → pipeline → chunking → indexing
- Track C (DevOps/MLOps): Terraform → CI/CD → Makefile → release records
- Track D (AI Engineer): FastAPI → streaming → auth → session memory
- Gate (Security): challenge mode on every security-critical component

**Clock-time blocker:** Azure provisioning (~2-3 hours). Tracks complete while Azure setup runs.

### Phase III — Integration
**Who:** Prasad + live Azure environment
**What:** Wire real credentials, run first end-to-end query, verify trace log

- Wire credentials via Key Vault (managed identity — never env vars)
- Run first end-to-end query through full agent graph
- Verify TraceContext populates on every invocation
- Run full eval harness — record baseline metrics
- Claude plays Data Analyst: analyze results, generate improvement backlog

### Phase IV — Delivery artifacts
**Who:** Claude generates, Prasad signs off
**What:** The ATO evidence package — accumulates throughout, complete at delivery

| Artifact | For whom | NIST control |
|---|---|---|
| Use case doc + acceptance criteria | Mission owner | SA-17 |
| System boundary document | ISSO / AO | SA-17 |
| NIST control mapping | Compliance team | CA-2 |
| Release records (immutable YAML) | AO / auditor | AU-2, CM-3 |
| Eval delta reports | Strategy director | CA-7 |
| GCCH readiness statement | Contracting officer | SC-28 |

### Phase V — Operations
**Who:** Automated (CI/CD) + Prasad (review)
**What:** Continuous monitoring, drift detection, improvement backlog

- Every deployment generates a release record (automated)
- Every eval run feeds the improvement backlog (Data Analyst mode)
- Drift detection: eval delta alerts on p95 spike or refusal rate climb
- Model EOL monitoring: 90-day advance warning on pinned version deprecation
- CLAUDE.md evolves: every production finding adds a constraint rule

---

## Role switching guide

| Trigger | Role mode | Claude does |
|---|---|---|
| Client meeting | Business Analyst | Use cases, acceptance criteria, stakeholder summary |
| New feature / node | ML Engineer | Plan mode → node stub → StepRecord logging |
| Data source change | Data Engineer | Connector, pipeline, ADLS inspection |
| Auth / permissions | Security | Challenge mode, SAST, NIST mapping |
| Eval results in | Data Analyst | Gap analysis, improvement backlog |
| Metric decision | Data Scientist | Eval design, threshold analysis |
| Terraform change | DevOps/MLOps | Plan review, release record |
| API / streaming | AI Engineer | FastAPI, auth, session memory |

---

## Portability

The process is permanent. Only the compliance label changes.

| Client type | Compliance | What changes in CLAUDE.md |
|---|---|---|
| Federal (GCCH) | NIST 800-53, FedRAMP High, ATO | GCCH endpoints, CUI handling, full NIST mapping |
| Federal (commercial) | NIST 800-53, FedRAMP Mod | Commercial endpoints, NIST subset |
| Financial services | SOC 2, FFIEC | SOC 2 control mapping |
| Healthcare | HIPAA, HITRUST | PHI handling, BAA requirements |
| Commercial | None mandatory | Eval discipline + release lineage only |
