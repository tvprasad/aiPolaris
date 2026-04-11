"""
agent/nodes/synthesizer.py — Synthesizer node.

OWNERSHIP (ADR-004):
  Reads : state["retrieved_chunks"], state["query"], state["session_context"]
  Writes: state["answer"], state["citations"]
  Never : call external tools, read credentials, modify trace log directly

CAPABILITY (ADR-002):
  allowed_tools: [] — operates on state only. No external calls.

LLM LAYER:
  Uses LangChain LCEL — ChatPromptTemplate | AzureChatOpenAI | JsonOutputParser.
  LangGraph orchestrates the node. LangChain handles prompt templating and
  structured output parsing within the node.
"""

import time
from pathlib import Path
from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import AzureChatOpenAI

from agent.state import AgentState, StepRecord
from agent.tools.manifests import SYNTHESIZER_MANIFEST  # noqa: F401
from api.config import Settings, get_settings

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "synthesizer_system.txt"
_system_prompt: str | None = None

_INSUFFICIENT = (
    "I don't have enough information in my knowledge base to answer this question accurately."
)


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = _PROMPT_PATH.read_text(encoding="utf-8").strip()
    return _system_prompt


def _build_user_message(
    query: str, chunks: list[dict[str, Any]], session_context: dict[str, Any] | None
) -> str:
    chunks_text = "\n\n".join(
        f"[{i + 1}] Title: {c.get('title', 'Unknown')}\n"
        f"Source: {c.get('source', '')}\n"
        f"Content: {c.get('content', '')}"
        for i, c in enumerate(chunks)
    )

    context_block = ""
    if session_context:
        context_block = (
            f"Session context:\n"
            f"Prior query: {session_context.get('last_query', '')}\n"
            f"Prior answer: {session_context.get('last_answer', '')}\n\n"
        )

    return f"{context_block}User query: {query}\n\nRetrieved chunks:\n{chunks_text}"


def _build_chain(settings: Settings) -> Runnable[dict[str, Any], Any]:
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
        model_kwargs={"max_tokens": settings.max_tokens},
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            ("human", "{user_message}"),
        ]
    )
    return prompt | llm | JsonOutputParser()


async def synthesizer_node(state: AgentState) -> AgentState:
    """
    Assembles the final answer and citations from retrieved chunks.

    No tool calls. Operates on state only.
    Appends StepRecord to trace before returning. ADR-004.
    Returns structured refusal if chunks are empty or LLM signals INSUFFICIENT_CONTEXT.
    """
    start = time.perf_counter()
    settings = get_settings()

    chunks = state.get("retrieved_chunks", [])

    input_summary = {
        "chunk_count": len(chunks),
        "query_length": len(state.get("query", "")),
        "has_session_context": state.get("session_context") is not None,
    }

    citations: list[dict[str, Any]]
    if not chunks:
        answer, citations = _INSUFFICIENT, []
    else:
        answer, citations = await _synthesize(
            query=state["query"],
            chunks=chunks,
            session_context=state.get("session_context"),
            settings=settings,
        )

    latency_ms = (time.perf_counter() - start) * 1000

    state["trace"].step_log.append(
        StepRecord(
            node_name="Synthesizer",
            input_hash=StepRecord.hash_content(input_summary),
            tool_calls=[],
            output_hash=StepRecord.hash_content(
                {"answer_length": len(answer), "citation_count": len(citations)}
            ),
            latency_ms=latency_ms,
        )
    )

    state["answer"] = answer
    state["citations"] = citations
    return state


async def _synthesize(
    query: str,
    chunks: list[dict[str, Any]],
    session_context: dict[str, Any] | None,
    settings: Settings,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Use LangChain LCEL to synthesize an answer from retrieved chunks.

    Chain: ChatPromptTemplate | AzureChatOpenAI | JsonOutputParser
    Temperature=0 for deterministic execution.
    Returns (INSUFFICIENT answer, []) if LLM signals insufficient context or parse fails.
    """
    chain = _build_chain(settings)

    try:
        parsed = await chain.ainvoke(
            {
                "system_prompt": _get_system_prompt(),
                "user_message": _build_user_message(query, chunks, session_context),
            }
        )

        answer: str = parsed.get("answer", "")
        citations: list[dict[str, Any]] = parsed.get("citations", [])

        if answer == "INSUFFICIENT_CONTEXT" or not answer:
            return _INSUFFICIENT, []

        return answer, citations if isinstance(citations, list) else []

    except Exception:
        return _INSUFFICIENT, []
