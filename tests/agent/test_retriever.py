"""
tests/agent/test_retriever.py — Retriever node unit tests.

All Azure AI Search calls are mocked by patching _search_index directly.
Tests verify:
- Results filtered by reranker score threshold (ADR-002)
- Deduplication by source document
- CapabilityViolationError on out-of-manifest tool call (ADR-002)
- StepRecord appended to trace (ADR-004)
- tool_calls list contains "ai_search_read"
- Empty endpoint returns [] without Azure calls
"""

from unittest.mock import AsyncMock, patch

import pytest

from agent.graph import create_initial_state
from agent.nodes.retriever import _MIN_RERANKER_SCORE, retriever_node
from agent.state import AgentState
from agent.tools.manifests import (
    PLANNER_MANIFEST,
    RETRIEVER_MANIFEST,
    CapabilityViolationError,
    check_capability,
)


def _make_state(sub_tasks: list[str]) -> AgentState:
    state = create_initial_state(query=" ".join(sub_tasks))
    state["sub_tasks"] = sub_tasks
    return state


def _make_chunk(title: str, source: str, score: float) -> dict:
    return {
        "title": title,
        "content": f"Content of {title}",
        "source": source,
        "last_modified": "2026-01-01",
        "reranker_score": score,
    }


@pytest.mark.asyncio
async def test_retriever_returns_chunks_from_search():
    """Retriever passes sub_tasks to _search_index and stores results in state."""
    state = _make_state(["data retention policy"])
    chunks = [_make_chunk("Policy Doc", "policy.pdf", 0.90)]

    with patch("agent.nodes.retriever._search_index", AsyncMock(return_value=chunks)):
        result = await retriever_node(state)

    assert result["retrieved_chunks"] == chunks


@pytest.mark.asyncio
async def test_retriever_empty_results_stored_correctly():
    """Empty results from _search_index stored as empty list, no error."""
    state = _make_state(["off-topic query"])

    with patch("agent.nodes.retriever._search_index", AsyncMock(return_value=[])):
        result = await retriever_node(state)

    assert result["retrieved_chunks"] == []


@pytest.mark.asyncio
async def test_retriever_appends_step_record_with_tool_call():
    """StepRecord with tool_calls=['ai_search_read'] appended to trace (ADR-004)."""
    state = _make_state(["test query"])
    chunks = [_make_chunk("Doc", "doc.pdf", 0.90)]

    with patch("agent.nodes.retriever._search_index", AsyncMock(return_value=chunks)):
        result = await retriever_node(state)

    assert len(result["trace"].step_log) == 1
    step = result["trace"].step_log[0]
    assert step.node_name == "Retriever"
    assert step.tool_calls == ["ai_search_read"]
    assert step.latency_ms >= 0


@pytest.mark.asyncio
async def test_search_index_filters_below_threshold():
    """_search_index filters results below reranker score threshold."""
    from agent.nodes.retriever import _search_index

    high = {
        "title": "High",
        "content": "c",
        "source": "h.pdf",
        "last_modified": "",
        "@search.reranker_score": 0.90,
    }
    low = {
        "title": "Low",
        "content": "c",
        "source": "l.pdf",
        "last_modified": "",
        "@search.reranker_score": 0.30,
    }

    async def mock_search_results(*a, **k):
        for r in [high, low]:
            yield r

    with (
        patch("azure.identity.DefaultAzureCredential"),
        patch("azure.search.documents.aio.SearchClient") as mock_client,
    ):
        mock_instance = AsyncMock()
        mock_instance.search.return_value = mock_search_results()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.nodes.retriever.get_settings") as mock_cfg:
            mock_cfg.return_value.search_endpoint = "https://fake.search.windows.net"
            mock_cfg.return_value.search_index_name = "test-index"

            results = await _search_index(["test query"])

    assert len(results) == 1
    assert results[0]["source"] == "h.pdf"
    assert results[0]["reranker_score"] >= _MIN_RERANKER_SCORE


@pytest.mark.asyncio
async def test_search_index_deduplicates_by_source():
    """_search_index deduplicates results with the same source."""
    from agent.nodes.retriever import _search_index

    dup_a = {
        "title": "Doc",
        "content": "c",
        "source": "doc.pdf",
        "last_modified": "",
        "@search.reranker_score": 0.90,
    }
    dup_b = {
        "title": "Doc",
        "content": "c",
        "source": "doc.pdf",
        "last_modified": "",
        "@search.reranker_score": 0.85,
    }

    call_count = 0

    async def mock_results(*a, **k):
        nonlocal call_count
        if call_count == 0:
            call_count += 1
            yield dup_a
        else:
            yield dup_b

    with (
        patch("azure.identity.DefaultAzureCredential"),
        patch("azure.search.documents.aio.SearchClient") as mock_client,
    ):
        mock_instance = AsyncMock()
        mock_instance.search.side_effect = lambda *a, **k: mock_results()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("agent.nodes.retriever.get_settings") as mock_cfg:
            mock_cfg.return_value.search_endpoint = "https://fake.search.windows.net"
            mock_cfg.return_value.search_index_name = "test-index"

            results = await _search_index(["task1", "task2"])

    sources = [r["source"] for r in results]
    assert sources.count("doc.pdf") == 1


@pytest.mark.asyncio
async def test_search_index_empty_endpoint_returns_empty():
    """Missing endpoint returns [] without touching Azure SDK."""
    from agent.nodes.retriever import _search_index

    with patch("agent.nodes.retriever.get_settings") as mock_cfg:
        mock_cfg.return_value.search_endpoint = ""
        mock_cfg.return_value.search_index_name = ""

        results = await _search_index(["test"])

    assert results == []


def test_capability_violation_error_for_planner_tool_access():
    """Planner has no allowed tools — any tool raises CapabilityViolationError (ADR-002)."""
    with pytest.raises(CapabilityViolationError):
        check_capability(PLANNER_MANIFEST, "ai_search_read")


def test_capability_violation_error_for_retriever_write_tool():
    """Retriever manifest must not allow write tools (ADR-002)."""
    with pytest.raises(CapabilityViolationError):
        check_capability(RETRIEVER_MANIFEST, "ai_search_write")


def test_retriever_manifest_allows_read_tool():
    """Retriever manifest explicitly allows ai_search_read."""
    check_capability(RETRIEVER_MANIFEST, "ai_search_read")  # must not raise
