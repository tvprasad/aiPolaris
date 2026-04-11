"""
tests/agent/test_graph.py — Unit tests for graph factory and initial state creation.
"""

from langgraph.graph import StateGraph

from agent.graph import build_graph, create_initial_state, graph
from agent.state import TraceContext


class TestCreateInitialState:
    def test_query_stored_correctly(self) -> None:
        state = create_initial_state("what is the policy?")
        assert state["query"] == "what is the policy?"

    def test_defaults_are_empty(self) -> None:
        state = create_initial_state("q")
        assert state["sub_tasks"] == []
        assert state["retrieved_chunks"] == []
        assert state["answer"] == ""
        assert state["citations"] == []

    def test_session_context_defaults_to_none(self) -> None:
        state = create_initial_state("q")
        assert state["session_context"] is None

    def test_user_oid_defaults_to_none(self) -> None:
        state = create_initial_state("q")
        assert state["user_oid"] is None

    def test_session_context_stored(self) -> None:
        ctx = {"last_query": "prior q", "last_answer": "prior a", "last_chunks": []}
        state = create_initial_state("new q", session_context=ctx)
        assert state["session_context"] == ctx

    def test_user_oid_stored(self) -> None:
        state = create_initial_state("q", user_oid="oid-abc-123")
        assert state["user_oid"] == "oid-abc-123"

    def test_trace_is_trace_context(self) -> None:
        state = create_initial_state("q")
        assert isinstance(state["trace"], TraceContext)

    def test_each_invocation_gets_new_trace_id(self) -> None:
        s1 = create_initial_state("q")
        s2 = create_initial_state("q")
        assert s1["trace"].trace_id != s2["trace"].trace_id

    def test_trace_step_log_starts_empty(self) -> None:
        state = create_initial_state("q")
        assert state["trace"].step_log == []


class TestBuildGraph:
    def test_returns_state_graph(self) -> None:
        g = build_graph()
        assert isinstance(g, StateGraph)


class TestCompiledGraph:
    def test_graph_is_not_none(self) -> None:
        assert graph is not None

    def test_graph_has_nodes(self) -> None:
        # The compiled graph exposes get_graph() for inspection
        mermaid = graph.get_graph().draw_mermaid()
        assert "planner" in mermaid
        assert "retriever" in mermaid
        assert "synthesizer" in mermaid
