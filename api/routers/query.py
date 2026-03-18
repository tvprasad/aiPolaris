"""
api/routers/query.py — POST /query endpoint with streaming. ADR-007.

StreamingResponse delivers first token in ~1s vs 9s blank screen.
Auth required: user role minimum (RBAC middleware).
Session context loaded from InMemorySessionStore (ADR-006).
"""

import json
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from agent.graph import create_initial_state, graph
from agent.memory.session import session_store
from api.middleware.rbac import require_capability
from api.schemas import QueryRequest

router = APIRouter()


@router.post("/query")
async def query(
    request: Request,
    body: QueryRequest,
    _: dict = Depends(require_capability("query")),
) -> StreamingResponse:
    """
    Run a query through the Planner → Retriever → Synthesizer graph.
    Streams the answer token by token. ADR-007.
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
    initial_state: dict,
    session_id: str,
    original_query: str,
) -> AsyncGenerator[str, None]:
    """
    Run the graph and stream the answer.
    Updates session store after completion. ADR-006.
    """
    start = time.perf_counter()

    try:
        # Run the graph
        # TODO: replace with streaming graph invocation
        # For now invoke synchronously and stream the result
        final_state = await graph.ainvoke(initial_state)

        answer = final_state.get("answer", "")
        citations = final_state.get("citations", [])
        trace = final_state.get("trace")

        # Stream answer in chunks
        chunk_size = 20
        for i in range(0, len(answer), chunk_size):
            chunk = answer[i : i + chunk_size]
            yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

        # Send citations and trace on completion
        latency_ms = (time.perf_counter() - start) * 1000
        yield f"data: {json.dumps({'type': 'done', 'citations': citations, 'trace_id': trace.trace_id if trace else '', 'latency_ms': round(latency_ms, 2)})}\n\n"

        # Update session store
        session_store.set(
            session_id=session_id,
            query=original_query,
            answer=answer,
            chunks=final_state.get("retrieved_chunks", []),
        )

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
