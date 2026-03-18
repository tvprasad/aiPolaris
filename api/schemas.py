"""
api/schemas.py — Pydantic request/response models.
All endpoints use these schemas. Never use raw dicts in route handlers.
"""

from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="UUID — creates new session if absent")


class CitationModel(BaseModel):
    chunk_id: str
    document_title: str
    source_site_id: str
    content_preview: str
    confidence: float


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationModel]
    trace_id: str
    session_id: str
    latency_ms: float


class IngestRequest(BaseModel):
    site_id: str = Field(..., description="SharePoint site ID to ingest")
    drive_id: str = Field(..., description="SharePoint drive ID")
    force_reindex: bool = Field(False, description="Re-index even if already indexed")


class IngestResponse(BaseModel):
    pull_id: str
    documents_pulled: int
    chunks_indexed: int
    errors: list[str]
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    environment: str
    index_document_count: int
