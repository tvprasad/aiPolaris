# Intake Prompt — Reusable Template

Use at the start of every engagement.
Fill in the eleven input fields from the client conversation or contract.
Paste into Claude. All eight artifacts generate simultaneously.

Covers all four federal agentic AI expertise areas:
Deterministic & Re-playable Execution · Secure Tooling & Capability Sandboxing ·
Latency Engineering Under Network Constraints · Change Management for AI Behavior

---

## The prompt

```
New engagement. Here are my inputs:

Objective      : [what the system needs to do — one paragraph]
Users          : [who uses it, what roles they hold, what they need]
Data sources   : [what data, sensitivity tier (CUI/PII/public),
                  where it lives, what connectors are needed]
Integrations   : [enterprise systems agent must connect to —
                  SharePoint, ServiceNow, Teams, Cyera, Armis, etc.]
Compliance     : [NIST 800-53 | FedRAMP High/Mod | SOC 2 | HIPAA |
                  CMMC | none — include ATO timeline if known]
Deployment     : [commercial Azure | GCCH | on-prem | hybrid —
                  include IL level if federal: IL2/IL4/IL5]
Stack          : [mandated technologies — LangGraph | SK | AutoGen |
                  specific Azure services | existing constraints]
Performance    : [p95 latency target | first token target |
                  token budget per query | streaming required Y/N |
                  GCCH: assume 1.5-2x commercial latency]
Change mgmt    : [prompt versioning policy | model pin policy |
                  rollback trigger conditions | drift alert thresholds |
                  shadow mode requirement Y/N]
Observability  : [telemetry stack | monitoring requirements |
                  alerting thresholds | ConMon reporting cadence]
Timeline       : [hard deadlines | ATO milestone | demo date]

Generate simultaneously:
1. Use case document
   (3-5 use cases, acceptance criteria per use case,
    actor definitions, success and failure conditions)

2. System boundary statement
   (in-scope components, out-of-scope, data flows,
    boundary note for ATO authorization package)

3. Threat model + capability boundaries
   (threat vectors, capability boundary per agent role,
    permission tiers, data sensitivity handling,
    GCCH-specific risks if applicable)

4. Eval acceptance criteria
   (metric thresholds: p50/p95 latency, confidence floor,
    correct/incorrect refusal rates, follow-up pass rate,
    replay match rate, capability violation test pass rate;
    golden question categories and counts)

5. CLAUDE.md draft
   (ADR constraints, stack, role-specific rules,
    never-do rules, performance SLOs, change mgmt policy)

6. ADR briefs
   (one per architectural decision implied by the stack:
    framework selection, read-only default, env-scoped endpoints,
    trace context, chunking, session memory, streaming,
    prompt pinning, model version pin, latency strategy,
    observability stack)

7. Latency budget + change management constraints
   (SLOs per endpoint, streaming requirement rationale,
    token budget per role, GCCH latency multiplier plan,
    prompt versioning policy, model EOL monitoring approach,
    shadow mode rollback triggers, behavioral drift thresholds)

8. NIST 800-53 control mapping table
   (every process artifact and CI gate mapped to its control:
    ADRs = CM-3, release records = AU-2/CM-3, SAST = SI-10/SA-11,
    RBAC = AC-2/AC-5, Key Vault = IA-5/SC-12, eval ConMon = CA-7,
    trace log = AU-2/IR-4, prompt hash = CM-3/SA-10,
    system boundary = SA-17, threat model = RA-3)
```

---

## What each field drives

**Objective**
→ UC titles and descriptions, system boundary in-scope section,
  CLAUDE.md project objective, README opening line

**Users + roles**
→ RBAC capability mapping (user/operator/admin),
  Entra ID role definitions in rbac.py, UC actor definitions

**Data sources + sensitivity**
→ System boundary data flows, threat model sensitivity tier,
  ADLS container structure, chunking strategy constraints,
  AI Search index schema decisions

**Integrations**
→ Connector ADRs (Graph API, ServiceNow, Cyera, Armis, MCP servers),
  pipeline architecture, Data Engineer mode work scope

**Compliance**
→ NIST control mapping table (Artifact 8), ADR consequences sections,
  CI gate requirements, release record fields, ATO milestone sequencing

**Deployment**
→ Terraform workspace structure, GCCH endpoint matrix (6 service pairs),
  authority URL, IL level determines GCCH service availability

**Stack**
→ ADR-001 (framework selection), pyproject.toml,
  CLAUDE.md stack section, agent tool manifest design

**Performance**
→ ADR for streaming (ADR-007), token budget in api/config.py,
  eval latency thresholds, GCCH multiplier (target × 1.5 minimum)

**Change management**
→ ADR for prompt pinning, ADR for model version pin,
  prompts.lock policy, CI prompt-integrity gate,
  release record prompt_hashes, drift alert thresholds,
  shadow mode rollback design

**Observability**
→ Telemetry integration (OTel/Prometheus/App Insights),
  StepRecord field design, ConMon eval run schedule,
  drift detection thresholds

**Timeline**
→ Eval threshold tightness, build phase sequencing,
  Azure provisioning lead time (2-3 hrs minimum)

---

## aiPolaris four expertise areas — coverage map

| Expertise area | Fields that drive it | Artifacts that satisfy it |
|---|---|---|
| Deterministic & Re-playable Execution | Stack, Change mgmt | ADR briefs (trace, prompt pin, model pin), CLAUDE.md, Artifact 7 |
| Secure Tooling & Capability Sandboxing | Users, Integrations, Compliance | Threat model, ADR briefs (read-only, manifests), Artifact 8 |
| Latency Engineering Under Network Constraints | Performance, Deployment | Eval criteria (latency thresholds), Artifact 7, ADR streaming |
| Change Management for AI Behavior | Change mgmt, Observability | Artifact 7, ADR prompt pin, Artifact 8 (CM-3, CA-7) |

---

## After running the prompt

1. Review all 8 artifacts — human sign-off required before any code starts
2. Lock CLAUDE.md — operating system for the engagement
3. Number and file each ADR brief in docs/adr/
4. Seed eval/golden_questions.json from Artifact 4
5. File docs/system-boundary.md from Artifact 2
6. File docs/nist-control-mapping.md from Artifact 8
7. Commit: git commit -m "feat: intake artifacts — [engagement name]"

---

## Portability — what changes per engagement

| Engagement | Compliance | Performance | Change mgmt |
|---|---|---|---|
| Federal GCCH | NIST 800-53, FedRAMP High, ATO | p95 < 4,000ms, ×1.5 GCCH | Prompt + model pin, shadow mode |
| Federal commercial | NIST 800-53, FedRAMP Mod | p95 < 4,000ms | Prompt + model pin |
| Healthcare | HIPAA, HITRUST | p95 < 3,000ms | Prompt pin required |
| Financial | SOC 2 Type II | p95 < 2,000ms | Audit trail required |
| Commercial | none | p95 < 3,000ms | Eval harness minimum |
