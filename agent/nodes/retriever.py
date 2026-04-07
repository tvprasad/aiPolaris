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
    check_capability,
)
from api.config import get_settings

# Confidence threshold: reranker score below this is not returned (ADR-002)
_MIN_RERANKER_SCORE = 0.60
_TOP_K = 5


async def retriever_node(state: AgentState) -> AgentState:
    """
    Executes sub-tasks against Azure AI Search (read-only hybrid search).

    Appends StepRecord to trace before returning. ADR-004.
    Raises CapabilityViolationError on any out-of-manifest tool. ADR-002.
    """
    start = time.perf_counter()

    tool_name = "ai_search_read"
    check_capability(RETRIEVER_MANIFEST, tool_name)

    input_summary = {"sub_tasks": state["sub_tasks"]}

    retrieved_chunks = await _search_index(
        sub_tasks=state["sub_tasks"],
    )

    latency_ms = (time.perf_counter() - start) * 1000

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
    Execute hybrid semantic search for each sub-task against Azure AI Search.
    Deduplicates results by source document. Returns top-K chunks above
    the confidence threshold.

    Uses managed identity (DefaultAzureCredential) — no API key in code.
    Azure SDK imports are deferred to avoid network probes at module load time.
    """
    from azure.identity import DefaultAzureCredential
    from azure.search.documents.aio import SearchClient

    settings = get_settings()

    if not settings.search_endpoint or not settings.search_index_name:
        return []

    credential = DefaultAzureCredential()
    all_chunks: list[dict] = []
    seen_sources: set[str] = set()

    async with SearchClient(
        endpoint=settings.search_endpoint,
        index_name=settings.search_index_name,
        credential=credential,
    ) as client:
        for query_text in sub_tasks:
            results = await client.search(
                search_text=query_text,
                query_type="semantic",
                semantic_configuration_name="default",
                query_language="en-us",
                top=_TOP_K,
                select=["title", "content", "source", "last_modified"],
            )

            async for result in results:
                reranker_score = result.get("@search.reranker_score") or 0.0
                if reranker_score < _MIN_RERANKER_SCORE:
                    continue

                source = result.get("source", "")
                if source in seen_sources:
                    continue
                seen_sources.add(source)

                all_chunks.append({
                    "title": result.get("title", ""),
                    "content": result.get("content", ""),
                    "source": source,
                    "last_modified": result.get("last_modified", ""),
                    "reranker_score": round(reranker_score, 4),
                })

    # Sort by reranker score descending, return top K overall
    all_chunks.sort(key=lambda c: c["reranker_score"], reverse=True)
    return all_chunks[:_TOP_K]
