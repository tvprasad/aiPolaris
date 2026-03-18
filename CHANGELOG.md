# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

Release records (immutable YAML in `/release_records/`) are the authoritative
deployment audit trail. This CHANGELOG is the human-readable companion.

---

## [Unreleased]

### Added
- Initial scaffold — CLAUDE.md, 9 ADRs, LangGraph DAG (Planner → Retriever → Synthesizer)
- AgentState schema with TraceContext and StepRecord (ADR-004)
- Tool manifests with CapabilityViolationError enforcement (ADR-002)
- InMemorySessionStore with TTL=1800s (ADR-006)
- FastAPI streaming endpoint /query (ADR-007)
- Entra ID auth middleware stub (NIST IA-2)
- RBAC capability middleware (NIST AC-5)
- Eval harness with 20 golden questions and p50/p95/refusal metrics
- Offline eval runner with smoke subset
- GCCH-scoped Terraform workspaces — commercial + gcch (ADR-003, ADR-009)
- CI/CD pipeline — lint, SAST, types, test, prompt-integrity, eval-smoke gates
- Immutable release record generator (NIST AU-2, CM-3)
- Pre-commit hooks — ruff, bandit, detect-secrets, mypy, prompt-integrity
- Graph API connector stub (pipeline/connectors/graph_api.py)
- Overlapping window chunker 512t/10% overlap (ADR-005)
- Claude skills — /new-adr, /new-agent-node, /new-eval-case, /gcch-check, /challenge-security
- PULL_REQUEST_TEMPLATE with security and eval checklists
- CODEOWNERS for security-critical paths
- Docker multi-stage build targeting AKS
- System boundary document and use cases (ATO intake artifacts)
- NIST 800-53 control mapping

### Security
- All Azure endpoints parameterized via Terraform (ADR-009)
- Prompt hash-pinning via prompts.lock (ADR-008)
- Bandit SAST + pip-audit + detect-secrets in CI

---

## Release format

Each release entry documents:
- What changed (Added / Changed / Deprecated / Removed / Fixed / Security)
- Which ADR it satisfies (if architectural)
- Which NIST control it addresses (if compliance)
- Eval delta if behavioral (p95 latency, incorrect_refusal_rate)

Example:
```
## [0.2.0] — 2026-04-01

### Added
- Real AI Search integration in Retriever node (ADR-002)
- Eval: p95 latency 4,200ms → 2,100ms after streaming fix (ADR-007)

### Security
- MSAL token validation implemented in auth.py (NIST IA-2)
  Challenge mode findings resolved: 3 bypasses found and fixed

### Fixed
- Follow-up query false refusals — session context now passed (ADR-006)
  Eval: follow-up pass rate 0% → 100%
```
