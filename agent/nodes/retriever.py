"""
agent/nodes/retriever.py — Retriever node.

OWNERSHIP (ADR-004):
  Reads : state["sub_tasks"]
  Writes: state["retrieved_chunks"]
  Never : access session_context, write answer, modify trace directly

CAPABILITY (ADR-002):
  allowed_tools: ["ai_search_read"] — read-only. No writes ever.
  Raises CapabilityViolationError on any out-of-manifest tool attempt.
"""

import time

from agent.state import AgentState, StepRecord
from agent.tools.manifests import (
    RETRIEVER_MANIFEST,
    CapabilityViolationError,
    check_capability,
)


async def retriever_node(state: AgentState) -> AgentState:
    """
    Executes sub-tasks against Azure AI Search (read-only).

    Appends StepRecord to trace before returning. ADR-004.
    Raises CapabilityViolationError on any out-of-manifest tool. ADR-002.
    """
    start = time.perf_counter()

    tool_name = "ai_search_read"
    check_capability(RETRIEVER_MANIFEST, tool_name)  # enforce manifest

    input_summary = {"sub_tasks": state["sub_tasks"]}

    # ── Core logic (replace stub with real AI Search call) ────────────────────
    retrieved_chunks: list[dict] = await _search_index(
        sub_tasks=state["sub_tasks"]
    )

    latency_ms = (time.perf_counter() - start) * 1000

    # ── Append StepRecord (ADR-004) ───────────────────────────────────────────
    state["trace"].step_log.append(
        StepRecord(
            node_name="Retriever",
            input_hash=StepRecord.hash_content(input_summary),
            tool_calls=[tool_name],
            output_hash=StepRecord.hash_content(retrieved_chunks),
            latency_ms=latency_ms,
        )
    )

    state["retrieved_chunks"] = retrieved_chunks
    return state


async def _search_index(sub_tasks: list[str]) -> list[dict]:
    """
    Stub: replace with real Azure AI Search call.
    Uses ai_search_read tool only — any other tool raises CapabilityViolationError.

    To test capability enforcement deliberately:
        check_capability(RETRIEVER_MANIFEST, "ai_search_write")  # raises
    """
    # TODO: implement Azure AI Search hybrid query
    # from agent.tools.ai_search_read import search
    # results = await search(queries=sub_tasks, top_k=5)
    return []
