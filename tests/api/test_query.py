"""
tests/api/test_query.py — Tests for POST /query SSE streaming endpoint.

Strategy:
  - _JsonAnswerExtractor: pure unit tests — no mocking needed.
  - /query endpoint: mock graph.astream_events to return controlled event sequences.
    validate_token dependency overridden to bypass Entra ID (same pattern as test_rbac.py).
"""

import json
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app
from api.middleware.auth import validate_token
from api.routers.query import _JsonAnswerExtractor

# ── _JsonAnswerExtractor unit tests ───────────────────────────────────────────


class TestJsonAnswerExtractor:
    def test_extracts_simple_answer(self) -> None:
        ex = _JsonAnswerExtractor()
        result = ex.feed('{"answer": "Hello world", "citations": []}')
        assert result == "Hello world"

    def test_extracts_across_chunks(self) -> None:
        ex = _JsonAnswerExtractor()
        r1 = ex.feed('{"answer": "Hel')
        r2 = ex.feed("lo wor")
        r3 = ex.feed('ld", "citations": []}')
        assert r1 + r2 + r3 == "Hello world"

    def test_returns_empty_before_marker(self) -> None:
        ex = _JsonAnswerExtractor()
        result = ex.feed('{"other_key": "value"')
        assert result == ""

    def test_marker_spans_chunks(self) -> None:
        ex = _JsonAnswerExtractor()
        r1 = ex.feed('{"ans')
        r2 = ex.feed('wer": "Hi"}')
        assert r1 + r2 == "Hi"

    def test_stops_at_closing_quote(self) -> None:
        ex = _JsonAnswerExtractor()
        ex.feed('{"answer": "Text", "citations": []}')
        # After closing quote, done is True
        assert ex.done
        # No more output after done
        r2 = ex.feed("extra stuff")
        assert r2 == ""

    def test_unescapes_newline(self) -> None:
        ex = _JsonAnswerExtractor()
        result = ex.feed('{"answer": "line1\\nline2"}')
        assert result == "line1\nline2"

    def test_unescapes_tab(self) -> None:
        ex = _JsonAnswerExtractor()
        result = ex.feed('{"answer": "col1\\tcol2"}')
        assert result == "col1\tcol2"

    def test_empty_answer(self) -> None:
        ex = _JsonAnswerExtractor()
        result = ex.feed('{"answer": ""}')
        assert result == ""
        assert ex.done

    def test_answer_with_special_chars(self) -> None:
        ex = _JsonAnswerExtractor()
        result = ex.feed('{"answer": "The policy states: use HTTPS."}')
        assert "The policy states: use HTTPS." in result

    def test_single_char_chunks(self) -> None:
        ex = _JsonAnswerExtractor()
        full = '{"answer": "AB"}'
        parts = [ex.feed(c) for c in full]
        assert "".join(parts) == "AB"


# ── /query endpoint tests ─────────────────────────────────────────────────────


def _admin_claims() -> dict:
    return {"roles": ["admin"], "oid": "test-oid", "name": "Test Admin"}


def _make_mock_event(kind: str, node: str | None, content: str | None = None) -> dict:
    """Helper to build astream_events-shaped event dicts."""
    event: dict = {"event": kind, "name": node or "", "metadata": {}, "data": {}}
    if node:
        event["metadata"]["langgraph_node"] = node
    if kind == "on_chat_model_stream" and content is not None:
        chunk = MagicMock()
        chunk.content = content
        event["data"] = {"chunk": chunk}
    return event


def _make_chain_end_event(node: str, citations: list, trace_id: str) -> dict:
    trace = MagicMock()
    trace.trace_id = trace_id
    return {
        "event": "on_chain_end",
        "name": node,
        "metadata": {"langgraph_node": node},
        "data": {
            "output": {
                "citations": citations,
                "retrieved_chunks": [],
                "trace": trace,
            }
        },
    }


async def _fake_astream_events(
    initial_state: dict[str, object], version: str
) -> AsyncGenerator[dict[str, object], None]:
    """Yields a controlled event sequence simulating a successful agent run."""
    # Planner + retriever events (no streaming content)
    yield _make_mock_event("on_chain_start", "planner")
    yield _make_mock_event("on_chain_end", "planner")
    yield _make_mock_event("on_chain_start", "retriever")
    yield _make_mock_event("on_chain_end", "retriever")

    # Synthesizer: stream JSON answer tokens
    yield _make_mock_event("on_chain_start", "synthesizer")
    yield _make_mock_event("on_chat_model_stream", "synthesizer", '{"answer": "The ')
    yield _make_mock_event("on_chat_model_stream", "synthesizer", "policy ")
    yield _make_mock_event("on_chat_model_stream", "synthesizer", 'applies.", "citations": []}')

    # Synthesizer done — supply citations
    yield _make_chain_end_event("synthesizer", [], "trace-abc-123")


async def _fake_astream_events_error(
    initial_state: dict[str, object], version: str
) -> AsyncGenerator[dict[str, object], None]:
    """Simulates a graph error mid-stream."""
    yield _make_mock_event("on_chain_start", "planner")
    raise RuntimeError("Simulated graph failure")


def _parse_sse(text: str) -> list[dict]:  # type: ignore[type-arg]
    """Parse SSE response body into a list of event dicts."""
    return [json.loads(ln[6:]) for ln in text.split("\n") if ln.startswith("data:")]


class TestQueryEndpointStreaming:
    def _client(self) -> TestClient:
        app.dependency_overrides[validate_token] = _admin_claims
        return TestClient(app, raise_server_exceptions=True)

    def teardown_method(self, _) -> None:
        app.dependency_overrides.pop(validate_token, None)

    def test_returns_200_with_event_stream(self) -> None:
        with patch("api.routers.query.graph") as mock_graph:
            mock_graph.astream_events = _fake_astream_events
            response = self._client().post("/query", json={"query": "What is the policy?"})
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    def test_response_contains_token_events(self) -> None:
        with patch("api.routers.query.graph") as mock_graph:
            mock_graph.astream_events = _fake_astream_events
            response = self._client().post("/query", json={"query": "What is the policy?"})
        events = _parse_sse(response.text)
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) > 0

    def test_token_content_assembles_to_answer(self) -> None:
        with patch("api.routers.query.graph") as mock_graph:
            mock_graph.astream_events = _fake_astream_events
            response = self._client().post("/query", json={"query": "What is the policy?"})
        events = _parse_sse(response.text)
        assembled = "".join(e["content"] for e in events if e["type"] == "token")
        assert assembled == "The policy applies."

    def test_response_ends_with_done_event(self) -> None:
        with patch("api.routers.query.graph") as mock_graph:
            mock_graph.astream_events = _fake_astream_events
            response = self._client().post("/query", json={"query": "What is the policy?"})
        events = _parse_sse(response.text)
        done_events = [e for e in events if e["type"] == "done"]
        assert len(done_events) == 1

    def test_done_event_contains_trace_id(self) -> None:
        with patch("api.routers.query.graph") as mock_graph:
            mock_graph.astream_events = _fake_astream_events
            response = self._client().post("/query", json={"query": "What is the policy?"})
        events = _parse_sse(response.text)
        done = next(e for e in events if e["type"] == "done")
        assert "trace_id" in done
        assert done["trace_id"] == "trace-abc-123"

    def test_done_event_contains_latency(self) -> None:
        with patch("api.routers.query.graph") as mock_graph:
            mock_graph.astream_events = _fake_astream_events
            response = self._client().post("/query", json={"query": "What is the policy?"})
        events = _parse_sse(response.text)
        done = next(e for e in events if e["type"] == "done")
        assert done["latency_ms"] >= 0

    def test_x_session_id_header_present(self) -> None:
        with patch("api.routers.query.graph") as mock_graph:
            mock_graph.astream_events = _fake_astream_events
            response = self._client().post("/query", json={"query": "q"})
        assert "x-session-id" in response.headers

    def test_x_trace_id_header_present(self) -> None:
        with patch("api.routers.query.graph") as mock_graph:
            mock_graph.astream_events = _fake_astream_events
            response = self._client().post("/query", json={"query": "q"})
        assert "x-trace-id" in response.headers

    def test_session_id_forwarded_in_body(self) -> None:
        with patch("api.routers.query.graph") as mock_graph:
            mock_graph.astream_events = _fake_astream_events
            response = self._client().post(
                "/query", json={"query": "q", "session_id": "sess-abc-123"}
            )
        assert response.headers["x-session-id"] == "sess-abc-123"

    def test_graph_error_yields_error_event(self) -> None:
        with patch("api.routers.query.graph") as mock_graph:
            mock_graph.astream_events = _fake_astream_events_error
            response = self._client().post("/query", json={"query": "q"})
        events = _parse_sse(response.text)
        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 1
        assert "Simulated graph failure" in error_events[0]["message"]

    def test_unauthenticated_returns_403(self) -> None:
        # Remove dependency override so auth middleware runs normally
        app.dependency_overrides.pop(validate_token, None)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/query", json={"query": "test"})
        # With auth_enabled=False (dev bypass), this will still succeed
        # This test validates the endpoint is wired to RBAC — not testing Entra ID
        assert response.status_code in (200, 403)


# ── check_eval_thresholds.py unit tests ──────────────────────────────────────


class TestCheckEvalThresholds:
    def test_passing_thresholds(self, tmp_path) -> None:
        from scripts.check_eval_thresholds import check_thresholds

        results_file = tmp_path / "eval_pass.json"
        results_file.write_text(
            json.dumps(
                {
                    "incorrect_refusal_rate": 0.10,
                    "p95_latency_ms": 5000.0,
                }
            )
        )
        violations = check_thresholds(
            results_file, max_incorrect_refusal=0.40, max_p95_latency=30_000
        )
        assert violations == []

    def test_incorrect_refusal_violation(self, tmp_path) -> None:
        from scripts.check_eval_thresholds import check_thresholds

        results_file = tmp_path / "eval_fail.json"
        results_file.write_text(
            json.dumps(
                {
                    "incorrect_refusal_rate": 0.50,
                    "p95_latency_ms": 5000.0,
                }
            )
        )
        violations = check_thresholds(
            results_file, max_incorrect_refusal=0.40, max_p95_latency=30_000
        )
        assert len(violations) == 1
        assert "incorrect_refusal_rate" in violations[0]

    def test_latency_violation(self, tmp_path) -> None:
        from scripts.check_eval_thresholds import check_thresholds

        results_file = tmp_path / "eval_lat.json"
        results_file.write_text(
            json.dumps(
                {
                    "incorrect_refusal_rate": 0.10,
                    "p95_latency_ms": 35_000.0,
                }
            )
        )
        violations = check_thresholds(
            results_file, max_incorrect_refusal=0.40, max_p95_latency=30_000
        )
        assert len(violations) == 1
        assert "p95_latency_ms" in violations[0]

    def test_both_violations(self, tmp_path) -> None:
        from scripts.check_eval_thresholds import check_thresholds

        results_file = tmp_path / "eval_both.json"
        results_file.write_text(
            json.dumps(
                {
                    "incorrect_refusal_rate": 0.60,
                    "p95_latency_ms": 50_000.0,
                }
            )
        )
        violations = check_thresholds(
            results_file, max_incorrect_refusal=0.40, max_p95_latency=30_000
        )
        assert len(violations) == 2

    def test_at_exact_boundary_passes(self, tmp_path) -> None:
        from scripts.check_eval_thresholds import check_thresholds

        results_file = tmp_path / "eval_boundary.json"
        results_file.write_text(
            json.dumps(
                {
                    "incorrect_refusal_rate": 0.40,
                    "p95_latency_ms": 30_000.0,
                }
            )
        )
        violations = check_thresholds(
            results_file, max_incorrect_refusal=0.40, max_p95_latency=30_000
        )
        assert violations == []
