"""
agent/nodes/planner.py — Planner node.

OWNERSHIP (ADR-004):
  Reads : state["query"], state["session_context"]
  Writes: state["sub_tasks"]
  Never : access data sources, call tools, write other fields

CAPABILITY (ADR-002):
  allowed_tools: [] — no tool access. Decomposition only.
"""

import time
from typing import Any

from agent.state import AgentState, StepRecord, TraceContext
from agent.tools.manifests import PLANNER_MANIFEST, CapabilityViolationError


async def planner_node(state: AgentState) -> AgentState:
    """
    Decomposes the user query into sub-tasks for the Retriever.

    No tool calls. No data access. Query + session context only.
    Appends StepRecord to trace before returning. ADR-004.
    """
    start = time.perf_counter()

    input_summary = {
        "query": state["query"],
        "has_session_context": state.get("session_context") is not None,
    }

    # ── Core logic (replace stub with LLM call) ───────────────────────────────
    # PLAN MODE NOTE: Implement after AgentState schema review.
    # Prompt lives in agent/prompts/planner_system.txt (hash-pinned, ADR-008)
    sub_tasks: list[str] = _decompose_query(
        query=state["query"],
        session_context=state.get("session_context"),
    )

    latency_ms = (time.perf_counter() - start) * 1000

    # ── Append StepRecord — required for all nodes (ADR-004) ─────────────────
    state["trace"].step_log.append(
        StepRecord(
            node_name="Planner",
            input_hash=StepRecord.hash_content(input_summary),
            tool_calls=[],  # Planner never calls tools
            output_hash=StepRecord.hash_content(sub_tasks),
            latency_ms=latency_ms,
        )
    )

    state["sub_tasks"] = sub_tasks
    return state


def _decompose_query(
    query: str,
    session_context: dict | None,
) -> list[str]:
    """
    Stub: replace with LLM call using agent/prompts/planner_system.txt.
    Must not make any tool calls — ADR-002, PLANNER_MANIFEST.
    """
    # TODO: call Azure OpenAI with planner_system.txt prompt
    # For now return query as single sub-task
    return [query]
