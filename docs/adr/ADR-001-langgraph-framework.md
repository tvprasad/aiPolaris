# ADR-001: LangGraph as Agent Orchestration Framework

**Date:** 2026-03-15
**Status:** Accepted
**Project:** aiPolaris

## Context
aiPolaris requires a multi-agent orchestration framework for a
Planner → Retriever → Synthesizer DAG with stateful execution,
conditional branching, and deterministic re-playable workflows.
Target: GCCH federal deployment requiring full audit trail and
capability sandboxing per agent node.

Four frameworks evaluated: LangGraph, LangChain, Semantic Kernel, AutoGen.

## Decision
**LangGraph.** Only framework with explicit state ownership by design —
prerequisite for capability sandboxing and deterministic replay in GCCH.

## Options Rejected
- **LangChain**: Chain-based, no explicit state ownership, harder to enforce
  capability boundaries across nodes.
- **Semantic Kernel**: Correct tool for M365 Copilot plugin development.
  Wrong tool for stateful federal RAG DAGs. Python SDK less mature than C#.
- **AutoGen**: Strong for conversational multi-agent patterns. Harder to
  enforce capability boundaries. Better for research than production federal.

## Consequences
- State schema designed before nodes — prevents mutation conflicts
- TraceContext integrates naturally into LangGraph AgentState
- Graph exports Mermaid diagram natively (make graph-viz)
- GCCH deployment: Python-native, no cloud-specific framework dependencies

## NIST mapping
CM-3 (configuration management of agent execution), AU-2 (audit trail),
AC-5 (separation of duties via node ownership boundaries)

## Interview answer
"I evaluated all four frameworks. LangGraph is right for stateful DAGs
where every node's state ownership must be explicit — that's a prerequisite
for the GCCH audit trail and capability sandboxing requirements. Semantic
Kernel is right when you're building into the M365 Copilot ecosystem.
Different use cases, different tools."
