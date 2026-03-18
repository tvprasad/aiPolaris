"""
api/config.py — Application settings.

All Azure endpoints read from environment variables populated
by Terraform outputs at deploy time. ZERO hardcoded URLs. ADR-009.

Never add a hardcoded Azure URL to this file.
Never read secrets from environment variables — Key Vault only.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment — set by Terraform workspace
    environment: str = "commercial"

    # Azure endpoints — populated from Terraform outputs (ADR-009)
    openai_endpoint: str = ""
    search_endpoint: str = ""
    graph_endpoint: str = ""
    adls_endpoint: str = ""
    keyvault_endpoint: str = ""
    authority: str = ""

    # Azure resource names
    openai_deployment: str = "gpt-4o"
    search_index_name: str = "enterprise-rag-index"
    adls_container_raw: str = "raw"
    adls_container_staged: str = "staged"

    # Entra ID
    auth_enabled: bool = True
    client_id: str = ""
    tenant_id: str = ""

    # Model config
    model_temperature: float = 0.0  # ADR-007: deterministic execution
    max_tokens: int = 1000
    confidence_threshold: float = 0.60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
