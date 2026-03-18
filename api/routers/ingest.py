"""
api/routers/ingest.py — POST /ingest endpoint.
Operator role required (RBAC middleware). ADR-002.
"""

import time
import uuid

from fastapi import APIRouter, Depends, Request

from api.middleware.rbac import require_capability
from api.schemas import IngestRequest, IngestResponse

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    request: Request,
    body: IngestRequest,
    _: dict = Depends(require_capability("ingest")),
) -> IngestResponse:
    """
    Trigger Graph API pull → ADLS staging → AI Search indexing.
    Operator role required — ADR-002 (read-only by default, write needs RBAC).
    """
    start = time.perf_counter()
    pull_id = str(uuid.uuid4())

    # TODO: wire to pipeline.connectors.graph_api + pipeline.indexing.ai_search
    # from pipeline.connectors.graph_api import GraphAPIConnector
    # from pipeline.indexing.ai_search import AISearchIndexer
    # connector = GraphAPIConnector()
    # docs = await connector.pull_site_documents(body.site_id, body.drive_id)
    # indexer = AISearchIndexer()
    # result = await indexer.upsert_chunks(docs)

    latency_ms = (time.perf_counter() - start) * 1000

    return IngestResponse(
        pull_id=pull_id,
        documents_pulled=0,
        chunks_indexed=0,
        errors=[],
        latency_ms=round(latency_ms, 2),
    )
