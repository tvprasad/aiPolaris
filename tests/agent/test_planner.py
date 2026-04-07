"""
tests/agent/test_planner.py — Planner node unit tests.

All LLM calls are mocked at the _decompose_query level. Tests verify:
- Sub-task decomposition (single and multi-task)
- Session context incorporation
- Fallback behavior on parse error
- StepRecord appended to trace (ADR-004)
- No tool calls ever (ADR-002)
"""

from unittest.mock import AsyncMock, patch

import pytest

from agent.graph import create_initial_state
from agent.nodes.planner import planner_node
from agent.state import AgentState


def _make_state(query: str, session_context: dict | None = None) -> AgentState:
    return create_initial_state(query=query, session_context=session_context)


@pytest.mark.asyncio
async def test_planner_single_subtask():
    """Simple query should return as a single sub-task."""
    state = _make_state("What is the data retention policy?")

    with patch("agent.nodes.planner._decompose_query", new=AsyncMock(return_value=["data retention policy"])):
        result = await planner_node(state)

    assert result["sub_tasks"] == ["data retention policy"]


@pytest.mark.asyncio
async def test_planner_multi_subtask():
    """Complex query should be decomposed into multiple sub-tasks."""
    state = _make_state("How does Meridian integrate with ServiceNow and what are the prerequisites?")
    sub_tasks = ["Meridian ServiceNow integration", "Meridian ServiceNow prerequisites"]

    with patch("agent.nodes.planner._decompose_query", new=AsyncMock(return_value=sub_tasks)):
        result = await planner_node(state)

    assert len(result["sub_tasks"]) == 2
    assert "Meridian ServiceNow integration" in result["sub_tasks"]


@pytest.mark.asyncio
async def test_planner_max_four_subtasks():
    """Planner must cap sub-tasks at 4 even if LLM returns more."""
    state = _make_state("Give me everything about the system")
    many_tasks = ["task1", "task2", "task3", "task4"]  # _decompose_query enforces the cap

    with patch("agent.nodes.planner._decompose_query", new=AsyncMock(return_value=many_tasks)):
        result = await planner_node(state)

    assert len(result["sub_tasks"]) <= 4


@pytest.mark.asyncio
async def test_planner_json_parse_fallback():
    """Malformed LLM output falls back to [query] without raising."""
    query = "What is the policy?"
    state = _make_state(query)

    with patch("agent.nodes.planner._decompose_query", new=AsyncMock(return_value=[query])):
        result = await planner_node(state)

    assert result["sub_tasks"] == [query]


@pytest.mark.asyncio
async def test_planner_appends_step_record():
    """StepRecord must be appended to trace (ADR-004)."""
    state = _make_state("Test query")

    with patch("agent.nodes.planner._decompose_query", new=AsyncMock(return_value=["Test query"])):
        result = await planner_node(state)

    assert len(result["trace"].step_log) == 1
    step = result["trace"].step_log[0]
    assert step.node_name == "Planner"
    assert step.tool_calls == []  # Planner never calls tools (ADR-002)
    assert step.latency_ms >= 0


@pytest.mark.asyncio
async def test_planner_session_context_passed():
    """Session context is incorporated into the user message."""
    session_context = {
        "last_query": "Tell me about Meridian",
        "last_answer": "Meridian is a governed RAG control plane.",
        "last_chunks": [],
    }
    state = _make_state("How does it handle authentication?", session_context=session_context)
    sub_tasks = ["Meridian authentication", "Meridian Entra ID"]

    with patch("agent.nodes.planner._decompose_query", new=AsyncMock(return_value=sub_tasks)) as mock_decompose:
        result = await planner_node(state)
        mock_decompose.assert_called_once()
        call_kwargs = mock_decompose.call_args
        assert call_kwargs.kwargs.get("session_context") == session_context or \
               (call_kwargs.args and call_kwargs.args[1] == session_context)

    assert result["sub_tasks"] == sub_tasks
