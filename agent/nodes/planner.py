"""
agent/nodes/planner.py — Planner node.

OWNERSHIP (ADR-004):
  Reads : state["query"], state["session_context"]
  Writes: state["sub_tasks"]
  Never : access data sources, call tools, write other fields

CAPABILITY (ADR-002):
  allowed_tools: [] — no tool access. Decomposition only.

LLM LAYER:
  Uses LangChain LCEL — ChatPromptTemplate | AzureChatOpenAI | JsonOutputParser.
  LangGraph orchestrates the node. LangChain handles prompt templating and
  structured output parsing within the node.
"""

import time
from pathlib import Path

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

from agent.state import AgentState, StepRecord
from agent.tools.manifests import PLANNER_MANIFEST  # noqa: F401 — manifest declared, no tools used
from api.config import get_settings

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "planner_system.txt"
_system_prompt: str | None = None


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = _PROMPT_PATH.read_text(encoding="utf-8").strip()
    return _system_prompt


def _build_user_message(query: str, session_context: dict | None) -> str:
    if session_context:
        return (
            f"Session context:\n"
            f"Prior query: {session_context.get('last_query', '')}\n"
            f"Prior answer: {session_context.get('last_answer', '')}\n\n"
            f"Current query: {query}"
        )
    return query


def _build_chain(settings):
    """
    Build the LCEL chain: ChatPromptTemplate | AzureChatOpenAI | JsonOutputParser.

    LangChain handles prompt templating and structured JSON output parsing.
    LangGraph orchestrates when this node runs and what state it receives.
    """
    llm = AzureChatOpenAI(
        azure_endpoint=settings.openai_endpoint,
        azure_deployment=settings.openai_deployment,
        api_version="2024-02-01",
        temperature=settings.model_temperature,
        max_tokens=256,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_prompt}"),
        ("human", "{user_message}"),
    ])
    return prompt | llm | JsonOutputParser()


async def planner_node(state: AgentState) -> AgentState:
    """
    Decomposes the user query into sub-tasks for the Retriever.

    No tool calls. No data access. Query + session context only.
    Appends StepRecord to trace before returning. ADR-004.
    """
    start = time.perf_counter()
    settings = get_settings()

    input_summary = {
        "query": state["query"],
        "has_session_context": state.get("session_context") is not None,
    }

    sub_tasks = await _decompose_query(
        query=state["query"],
        session_context=state.get("session_context"),
        settings=settings,
    )

    latency_ms = (time.perf_counter() - start) * 1000

    state["trace"].step_log.append(
        StepRecord(
            node_name="Planner",
            input_hash=StepRecord.hash_content(input_summary),
            tool_calls=[],
            output_hash=StepRecord.hash_content(sub_tasks),
            latency_ms=latency_ms,
        )
    )

    state["sub_tasks"] = sub_tasks
    return state


async def _decompose_query(
    query: str,
    session_context: dict | None,
    settings,
) -> list[str]:
    """
    Use LangChain LCEL to decompose the query into retrieval sub-tasks.

    Chain: ChatPromptTemplate | AzureChatOpenAI | JsonOutputParser
    Temperature=0 for deterministic execution.
    Falls back to [query] on any parse error — never raises to caller.
    """
    chain = _build_chain(settings)

    try:
        result = await chain.ainvoke({
            "system_prompt": _get_system_prompt(),
            "user_message": _build_user_message(query, session_context),
        })

        if isinstance(result, list) and all(isinstance(t, str) for t in result):
            return result[:4]  # enforce max 4 per prompt spec

    except Exception:
        pass

    # Fallback: treat entire query as single sub-task
    return [query]
