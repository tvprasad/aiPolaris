"""
api/main.py — FastAPI application entry point.

Streaming enabled on /query. ADR-007.
All endpoints require auth except /health. ADR (auth middleware).
RBAC enforced per endpoint capability. ADR-002.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings
from api.routers import health, ingest, query


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle."""
    settings = get_settings()
    # TODO: warm up Azure AI Search client
    # TODO: verify Key Vault connectivity
    print(f"Starting in {settings.environment} environment")
    yield
    print("Shutting down")


app = FastAPI(
    title="Enterprise Agentic RAG",
    description=(
        "Production-grade agentic RAG — LangGraph multi-agent system "
        "with Graph API ingestion, ADLS Gen2 staging, Azure AI Search, "
        "Entra ID auth, and GCCH-ready Terraform."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(query.router, tags=["query"])
app.include_router(ingest.router, tags=["ingest"])
