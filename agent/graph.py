"""
agent/graph.py — LangGraph DAG definition.

Graph: Planner → Retriever → Synthesizer

To visualize the graph:
    python -c "from agent.graph import graph; print(graph.get_graph().draw_mermaid())"
    # or: make graph-viz
"""

from typing import Any

from langgraph.graph import END, StateGraph

from agent.nodes.planner import planner_node
from agent.nodes.retriever import retriever_node
from agent.nodes.synthesizer import synthesizer_node
from agent.state import AgentState, TraceContext


def build_graph() -> "StateGraph[AgentState, Any, Any, Any]":
    """
    Build the Planner → Retriever → Synthesizer DAG.

    State ownership per node is documented in agent/state.py.
    All nodes are read-only by default (ADR-002).
    All nodes append StepRecord to trace (ADR-004).
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("synthesizer", synthesizer_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "retriever")
    workflow.add_edge("retriever", "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow


def create_initial_state(
    query: str,
    session_context: dict[str, object] | None = None,
    user_oid: str | None = None,
) -> AgentState:
    """
    Factory for initial AgentState with a fresh TraceContext.
    Every invocation gets a new trace_id (ADR-004).
    """
    return AgentState(
        query=query,
        session_context=session_context,
        user_oid=user_oid,
        sub_tasks=[],
        retrieved_chunks=[],
        answer="",
        citations=[],
        trace=TraceContext(),
    )


# Compile the graph — exported for use in API layer and eval harness
graph = build_graph().compile()
