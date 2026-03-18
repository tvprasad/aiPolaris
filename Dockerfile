# Dockerfile
# Multi-stage build — slim production image.
# Targets Azure Container Apps. ADR-003: GCCH-ready via env vars at runtime.
# Image must be digest-pinned in release records — never use 'latest' tag.

# ── Stage 1: build dependencies ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only what pip needs to resolve dependencies (cache-friendly layer)
COPY pyproject.toml .
COPY agent/     ./agent/
COPY api/       ./api/
COPY pipeline/  ./pipeline/

RUN pip install --no-cache-dir --upgrade pip setuptools \
    && pip install --no-cache-dir --target /deps .

# ── Stage 2: production image ─────────────────────────────────────────────────
FROM python:3.12-slim AS production

# Non-root user — NIST AC-6 least privilege
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages

# Copy application code
COPY --chown=appuser:appuser agent/     ./agent/
COPY --chown=appuser:appuser api/       ./api/
COPY --chown=appuser:appuser pipeline/  ./pipeline/
COPY --chown=appuser:appuser scripts/   ./scripts/
COPY --chown=appuser:appuser prompts.lock .

# No secrets in image — all via Key Vault + managed identity at runtime
# No .env file copied — ADR-003, NIST IA-5

USER appuser

# Health check — used by Container Apps liveness probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--no-access-log"]
