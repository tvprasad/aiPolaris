# ADR-010: Agent Spec Export via pyagentspec

**Date:** 2026-04-06
**Status:** Accepted
**Project:** aiPolaris

## Context

aiPolaris targets GCCH federal deployment. Compliance reviewers require a
human-readable, auditable declaration of what each agent does: its tools,
capabilities, and boundaries. Today the only artifact is Python source code.

Oracle's open Agent Spec (github.com/oracle/agent-spec) defines a portable,
framework-agnostic YAML schema for describing agents and workflows. The
`pyagentspec` SDK provides `AgentSpecExporter`, which accepts a compiled
LangGraph graph and emits a conformant Agent Spec YAML document with zero
changes to the existing DAG.

## Decision

Add `pyagentspec` as a runtime dependency. Export the compiled aiPolaris
LangGraph graph to Agent Spec YAML as part of every release record
(via `scripts/generate_release_record.py`).

The YAML export is an artifact only. It does not replace or alter the
LangGraph runtime (ADR-001 stands). The DAG continues to execute via
LangGraph as designed.

## Options Rejected

- **Adopt pyagentspec as runtime (AgentSpecLoader):** Replaces LangGraph as
  the execution engine. Rejected — violates ADR-001, loses explicit state
  ownership guarantees required for GCCH capability sandboxing.
- **Hand-author agent spec YAML:** Manual, drift-prone, not authoritative.
  Rejected — machine-generated from the running graph is the only trustworthy
  source.
- **No agent spec export:** Leaves compliance reviewers with Python source
  only. Rejected — a declarative spec document is a stronger audit artifact
  for GCCH accreditation packages.

## Consequences

- `pyagentspec` added to `[project.dependencies]` in `pyproject.toml`.
- `scripts/generate_release_record.py` emits `release/agent-spec.yaml`
  alongside the existing release manifest.
- `agent-spec.yaml` is pinned per release and included in the release
  lineage (ADR-008 extended: spec hash added to `prompts.lock`).
- Adding or removing a tool from any node requires a new release record
  and an ADR bump — the spec hash mismatch enforces this at CI time.

## NIST mapping

CM-3 (configuration change control — agent definition is versioned and
hashed), AU-2 (auditable event: agent capability declaration per release),
SA-17 (developer security architecture — portable spec decouples audit
from implementation language).

## Interview answer

"The LangGraph DAG is the runtime. The Agent Spec YAML is the audit
artifact. One export call on the compiled graph gives compliance reviewers
a human-readable, hash-pinned declaration of every tool, capability, and
boundary the agent has — without changing how it executes. That is the
right separation for a federal accreditation package."
