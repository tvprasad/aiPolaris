"""
api/routers/query.py — POST /query endpoint with true token-by-token streaming. ADR-007.

Streaming implementation:
  - graph.astream_events() yields on_chat_model_stream events as Azure OpenAI produces tokens.
  - _JsonAnswerExtractor decodes the streaming JSON to surface only answer-text tokens to SSE.
  - Citations and trace data arrive from the synthesizer on_chain_end event.
  - Session store is updated after streaming completes. ADR-006.

Auth required: user role minimum (RBAC middleware).
"""

import json
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from agent.graph import create_initial_state, graph
from agent.memory.session import session_store
from agent.state import AgentState
from api.middleware.rbac import require_capability
from api.schemas import QueryRequest

router = APIRouter()


# ── JSON answer extractor ─────────────────────────────────────────────────────


class _JsonAnswerExtractor:
    """
    Incrementally extracts the value of the "answer" key from a streaming JSON object.

    Azure OpenAI with response_format=json_object streams tokens that together form:
        {"answer": "The policy states...", "citations": [...]}

    This extractor buffers incoming chunks and yields only the answer text characters
    in real time — no buffering until complete JSON, no double LLM call.

    State machine:
        SEEKING        → scanning for "answer": marker
        AWAITING_QUOTE → marker found, waiting for the opening " of the value
        IN_VALUE       → inside the answer string value, emitting chars
        DONE           → closing quote reached, stop emitting
    """

    _MARKER = '"answer":'

    def __init__(self) -> None:
        self._buf: str = ""
        self._state: str = "SEEKING"  # SEEKING | AWAITING_QUOTE | IN_VALUE | DONE
        self._escape_next: bool = False

    def feed(self, chunk: str) -> str:
        """Feed a token chunk; return extracted answer characters (may be empty)."""
        if self._state == "DONE":
            return ""

        self._buf += chunk
        result: list[str] = []

        if self._state == "SEEKING":
            idx = self._buf.find(self._MARKER)
            if idx == -1:
                # Keep rolling tail so marker can span chunk boundaries
                self._buf = self._buf[-(len(self._MARKER) - 1) :]
                return ""
            # Marker found — advance past it
            self._buf = self._buf[idx + len(self._MARKER) :]
            self._state = "AWAITING_QUOTE"

        if self._state == "AWAITING_QUOTE":
            quote_idx = self._buf.find('"')
            if quote_idx == -1:
                # Opening quote not yet in buffer — keep everything
                return ""
            # Opening quote found — enter value
            self._buf = self._buf[quote_idx + 1 :]  # chars after opening quote
            self._state = "IN_VALUE"

        if self._state == "IN_VALUE":
            for char in self._buf:
                if self._escape_next:
                    # Unescape common JSON escape sequences
                    if char == "n":
                        result.append("\n")
                    elif char == "t":
                        result.append("\t")
                    elif char == "r":
                        result.append("\r")
                    else:
                        result.append(char)
                    self._escape_next = False
                elif char == "\\":
                    self._escape_next = True
                elif char == '"':
                    # Closing quote — done extracting
                    self._state = "DONE"
                    self._buf = ""
                    break
                else:
                    result.append(char)
            if self._state == "IN_VALUE":
                self._buf = ""  # all chars processed

        return "".join(result)

    @property
    def done(self) -> bool:
        return self._state == "DONE"


# ── Router ────────────────────────────────────────────────────────────────────


@router.post("/query")
async def query(
    request: Request,
    body: QueryRequest,
    _: dict[str, object] = Depends(require_capability("query")),
) -> StreamingResponse:
    """
    Run a query through the Planner → Retriever → Synthesizer graph.
    Streams answer tokens via SSE as Azure OpenAI produces them. ADR-007.
    Session context loaded if session_id provided. ADR-006.
    """
    session_id = body.session_id or str(uuid.uuid4())
    session_context = session_store.get(session_id)

    initial_state = create_initial_state(
        query=body.query,
        session_context=session_context,
        user_oid=getattr(request.state, "user_oid", None),
    )

    return StreamingResponse(
        _stream_response(initial_state, session_id, body.query),
        media_type="text/event-stream",
        headers={
            "X-Session-Id": session_id,
            "X-Trace-Id": initial_state["trace"].trace_id,
            "Cache-Control": "no-cache",
        },
    )


async def _stream_response(
    initial_state: "AgentState",
    session_id: str,
    original_query: str,
) -> AsyncGenerator[str, None]:
    """
    Run the graph with astream_events(), streaming answer tokens as they arrive.

    Token flow:
      Azure OpenAI → on_chat_model_stream → _JsonAnswerExtractor → SSE token event

    Citation + trace flow:
      synthesizer on_chain_end → SSE done event

    Session store updated on completion. ADR-006.
    """
    start = time.perf_counter()
    extractor = _JsonAnswerExtractor()
    answer_parts: list[str] = []

    # Final values populated from synthesizer node completion event
    citations: list[Any] = []
    trace_id: str = initial_state["trace"].trace_id
    retrieved_chunks: list[Any] = []

    try:
        async for event in graph.astream_events(initial_state, version="v2"):
            kind: str = event["event"]

            # ── Token streaming ───────────────────────────────────────────────
            if kind == "on_chat_model_stream":
                node = event.get("metadata", {}).get("langgraph_node", "")
                if node == "synthesizer" and not extractor.done:
                    raw_content: str = event["data"]["chunk"].content or ""
                    if raw_content:
                        extracted = extractor.feed(raw_content)
                        if extracted:
                            answer_parts.append(extracted)
                            yield f"data: {json.dumps({'type': 'token', 'content': extracted})}\n\n"

            # ── Synthesizer completion — captures citations + trace ────────────
            elif kind == "on_chain_end" and event.get("name") == "synthesizer":
                output: dict[str, Any] = event["data"].get("output", {})
                citations = output.get("citations", [])
                retrieved_chunks = output.get("retrieved_chunks", [])
                trace = output.get("trace")
                if trace:
                    trace_id = trace.trace_id

        # If no tokens were streamed (e.g. insufficient context refusal),
        # the answer lives in citations-less synthesizer state — already handled
        # by the extractor returning empty. Final answer assembled from parts.
        answer = "".join(answer_parts)

        latency_ms = (time.perf_counter() - start) * 1000
        yield (
            f"data: {json.dumps({'type': 'done', 'citations': citations, 'trace_id': trace_id, 'latency_ms': round(latency_ms, 2)})}\n\n"
        )

        # Update session store — memory only, never written to disk (ADR-007)
        session_store.set(
            session_id=session_id,
            query=original_query,
            answer=answer,
            chunks=retrieved_chunks,
        )

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
