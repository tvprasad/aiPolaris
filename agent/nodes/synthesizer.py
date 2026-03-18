"""
agent/nodes/synthesizer.py — Synthesizer node.

OWNERSHIP (ADR-004):
  Reads : state["retrieved_chunks"], state["query"], state["session_context"]
  Writes: state["answer"], state["citations"]
  Never : call external tools, read credentials, modify trace log directly

CAPABILITY (ADR-002):
  allowed_tools: [] — operates on state only. No external calls.
"""

import time

from agent.state import AgentState, StepRecord
from agent.tools.manifests import SYNTHESIZER_MANIFEST


async def synthesizer_node(state: AgentState) -> AgentState:
    """
    Assembles the final answer and citations from retrieved chunks.

    No tool calls. Operates on state only.
    Appends StepRecord to trace before returning. ADR-004.
    Gracefully handles empty retrieved_chunks (returns structured refusal).
    """
    start = time.perf_counter()

    input_summary = {
        "chunk_count": len(state.get("retrieved_chunks", [])),
        "query_length": len(state.get("query", "")),
        "has_session_context": state.get("session_context") is not None,
    }

    # ── Core logic (replace stub with LLM call) ───────────────────────────────
    # Prompt lives in agent/prompts/synthesizer_system.txt (hash-pinned, ADR-008)
    answer, citations = _synthesize(
        query=state["query"],
        chunks=state.get("retrieved_chunks", []),
        session_context=state.get("session_context"),
    )

    latency_ms = (time.perf_counter() - start) * 1000

    # ── Append StepRecord (ADR-004) ───────────────────────────────────────────
    state["trace"].step_log.append(
        StepRecord(
            node_name="Synthesizer",
            input_hash=StepRecord.hash_content(input_summary),
            tool_calls=[],  # Synthesizer never calls tools
            output_hash=StepRecord.hash_content(
                {"answer_length": len(answer), "citation_count": len(citations)}
            ),
            latency_ms=latency_ms,
        )
    )

    state["answer"] = answer
    state["citations"] = citations
    return state


def _synthesize(
    query: str,
    chunks: list[dict],
    session_context: dict | None,
) -> tuple[str, list[dict]]:
    """
    Stub: replace with LLM call using agent/prompts/synthesizer_system.txt.
    Must not make any tool calls — ADR-002, SYNTHESIZER_MANIFEST.

    Returns (answer, citations). If chunks is empty, returns a
    structured refusal — not an error. Refusals are correct behavior
    for out-of-scope queries.
    """
    if not chunks:
        return (
            "I don't have enough information in my knowledge base to "
            "answer this question accurately.",
            [],
        )

    # TODO: call Azure OpenAI with synthesizer_system.txt prompt
    return "Stub answer — implement LLM synthesis.", []
