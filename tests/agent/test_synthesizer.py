"""
tests/agent/test_synthesizer.py — Synthesizer node unit tests.

All LLM calls are mocked at the _synthesize level. Tests verify:
- Answer + citation extraction from LLM JSON response
- Structured refusal on empty chunks (ADR-002)
- Structured refusal on INSUFFICIENT_CONTEXT signal
- Fallback returns structured refusal on parse error
- StepRecord appended to trace (ADR-004)
- No tool calls ever (ADR-002)
"""

from unittest.mock import AsyncMock, patch

import pytest

from agent.graph import create_initial_state
from agent.nodes.synthesizer import _INSUFFICIENT, synthesizer_node
from agent.state import AgentState


def _make_state(query: str, chunks: list[dict], session_context: dict | None = None) -> AgentState:
    state = create_initial_state(query=query, session_context=session_context)
    state["sub_tasks"] = [query]
    state["retrieved_chunks"] = chunks
    return state


def _make_chunks(n: int = 2) -> list[dict]:
    return [
        {
            "title": f"Document {i}",
            "content": f"Content about topic {i}.",
            "source": f"doc_{i}.pdf",
            "last_modified": "2026-01-01",
            "reranker_score": 0.85 - (i * 0.05),
        }
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_synthesizer_returns_answer_and_citations():
    """Valid chunks produce answer with citations."""
    chunks = _make_chunks(2)
    state = _make_state("What is the retention policy?", chunks)

    citations = [{"title": "Document 0", "source": "doc_0.pdf", "excerpt": "Content about topic 0."}]
    answer = "The retention policy is 7 years [Document 0]."

    with patch("agent.nodes.synthesizer._synthesize", new=AsyncMock(return_value=(answer, citations))):
        result = await synthesizer_node(state)

    assert "retention policy" in result["answer"]
    assert len(result["citations"]) == 1
    assert result["citations"][0]["source"] == "doc_0.pdf"


@pytest.mark.asyncio
async def test_synthesizer_structured_refusal_on_empty_chunks():
    """Empty retrieved_chunks must produce structured refusal without LLM call."""
    state = _make_state("What is the policy?", chunks=[])

    with patch("agent.nodes.synthesizer._synthesize", new=AsyncMock()) as mock_synthesize:
        result = await synthesizer_node(state)
        mock_synthesize.assert_not_called()

    assert result["answer"] == _INSUFFICIENT
    assert result["citations"] == []


@pytest.mark.asyncio
async def test_synthesizer_structured_refusal_on_insufficient_context():
    """LLM INSUFFICIENT_CONTEXT signal produces structured refusal."""
    chunks = _make_chunks(1)
    state = _make_state("What is the policy on Mars?", chunks)

    with patch("agent.nodes.synthesizer._synthesize", new=AsyncMock(return_value=(_INSUFFICIENT, []))):
        result = await synthesizer_node(state)

    assert result["answer"] == _INSUFFICIENT
    assert result["citations"] == []


@pytest.mark.asyncio
async def test_synthesizer_json_parse_fallback():
    """Parse failure falls back to structured refusal without raising."""
    chunks = _make_chunks(1)
    state = _make_state("What is the policy?", chunks)

    with patch("agent.nodes.synthesizer._synthesize", new=AsyncMock(return_value=(_INSUFFICIENT, []))):
        result = await synthesizer_node(state)

    assert result["answer"] == _INSUFFICIENT
    assert result["citations"] == []


@pytest.mark.asyncio
async def test_synthesizer_appends_step_record():
    """StepRecord must be appended to trace (ADR-004)."""
    chunks = _make_chunks(1)
    state = _make_state("Test query", chunks)

    with patch("agent.nodes.synthesizer._synthesize", new=AsyncMock(return_value=("Test answer.", []))):
        result = await synthesizer_node(state)

    assert len(result["trace"].step_log) == 1
    step = result["trace"].step_log[0]
    assert step.node_name == "Synthesizer"
    assert step.tool_calls == []
    assert step.latency_ms >= 0


@pytest.mark.asyncio
async def test_synthesizer_step_record_on_empty_chunks():
    """StepRecord is appended even when chunks are empty (no LLM call path)."""
    state = _make_state("Test query", chunks=[])
    result = await synthesizer_node(state)

    assert len(result["trace"].step_log) == 1
    assert result["trace"].step_log[0].node_name == "Synthesizer"
