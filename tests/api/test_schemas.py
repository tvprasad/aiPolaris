"""
tests/api/test_schemas.py — Unit tests for Pydantic request/response schemas.
"""

import pytest
from pydantic import ValidationError

from api.schemas import (
    CitationModel,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
)


class TestQueryRequest:
    def test_valid_query(self) -> None:
        req = QueryRequest(query="What is the policy?")
        assert req.query == "What is the policy?"

    def test_session_id_optional(self) -> None:
        req = QueryRequest(query="q")
        assert req.session_id is None

    def test_session_id_stored(self) -> None:
        req = QueryRequest(query="q", session_id="abc-123")
        assert req.session_id == "abc-123"

    def test_empty_query_raises(self) -> None:
        with pytest.raises(ValidationError):
            QueryRequest(query="")

    def test_query_too_long_raises(self) -> None:
        with pytest.raises(ValidationError):
            QueryRequest(query="x" * 2001)

    def test_query_at_max_length_is_valid(self) -> None:
        req = QueryRequest(query="x" * 2000)
        assert len(req.query) == 2000


class TestIngestRequest:
    def test_defaults_force_reindex_false(self) -> None:
        req = IngestRequest(site_id="site-1", drive_id="drive-1")
        assert req.force_reindex is False

    def test_force_reindex_can_be_set(self) -> None:
        req = IngestRequest(site_id="s", drive_id="d", force_reindex=True)
        assert req.force_reindex is True

    def test_site_id_and_drive_id_required(self) -> None:
        with pytest.raises(ValidationError):
            IngestRequest(site_id="s")  # type: ignore[call-arg]


class TestHealthResponse:
    def test_fields_stored(self) -> None:
        resp = HealthResponse(status="ok", environment="commercial", index_document_count=42)
        assert resp.status == "ok"
        assert resp.environment == "commercial"
        assert resp.index_document_count == 42


class TestCitationModel:
    def test_fields_stored(self) -> None:
        c = CitationModel(
            chunk_id="cid-1",
            document_title="Policy Doc",
            source_site_id="site-1",
            content_preview="The policy states...",
            confidence=0.85,
        )
        assert c.chunk_id == "cid-1"
        assert c.confidence == 0.85


class TestQueryResponse:
    def test_fields_stored(self) -> None:
        resp = QueryResponse(
            answer="The answer is X.",
            citations=[],
            trace_id="trace-abc",
            session_id="sess-123",
            latency_ms=250.5,
        )
        assert resp.answer == "The answer is X."
        assert resp.trace_id == "trace-abc"
        assert resp.latency_ms == 250.5


class TestIngestResponse:
    def test_fields_stored(self) -> None:
        resp = IngestResponse(
            pull_id="pull-1",
            documents_pulled=10,
            chunks_indexed=120,
            errors=[],
            latency_ms=1500.0,
        )
        assert resp.pull_id == "pull-1"
        assert resp.documents_pulled == 10
        assert resp.chunks_indexed == 120
        assert resp.errors == []
