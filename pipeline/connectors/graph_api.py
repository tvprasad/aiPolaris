"""
pipeline/connectors/graph_api.py — Microsoft Graph API connector.

Pulls documents from SharePoint via managed identity auth. ADR-002.
Credentials fetched from Key Vault at runtime — never from env vars.
Writes raw documents to ADLS Gen2 raw/ container.

NIST AC-6: Read-only scope only — Sites.Read.All, Files.Read.All.
Nothing else. Any write scope requires a new ADR.
"""

import time
import uuid
from dataclasses import dataclass

from api.config import get_settings


@dataclass
class DocumentMetadata:
    document_id: str
    filename: str
    site_id: str
    drive_id: str
    size_bytes: int
    modified_at: str
    adls_path: str
    pull_id: str


class GraphAPIConnector:
    """
    Pulls documents from SharePoint into ADLS Gen2 raw/ container.

    Auth: MSAL ConfidentialClientApplication with client_secret
    fetched from Key Vault via managed identity. ADR-002.

    Scope: Sites.Read.All, Files.Read.All only.
    Any write scope is a capability violation under ADR-002.
    """

    READ_ONLY_SCOPES = [
        "https://graph.microsoft.com/Sites.Read.All",
        "https://graph.microsoft.com/Files.Read.All",
    ]

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None  # lazy init after Key Vault fetch

    async def pull_site_documents(
        self,
        site_id: str,
        drive_id: str,
    ) -> list[DocumentMetadata]:
        """
        Pull all documents from a SharePoint site/drive into ADLS raw/.

        Returns list of DocumentMetadata for each pulled document.
        Every pull gets a pull_id for audit trail linkage.

        Use Tip 9 inspection after running:
          "How many documents landed in ADLS raw/{site_id}/?"
          "Are there any documents in raw/ with no corresponding staged/ entry?"
        """
        pull_id = str(uuid.uuid4())
        start = time.perf_counter()

        # TODO: implement Graph API pull
        # 1. Get token from Key Vault via managed identity
        # 2. Build MSAL ConfidentialClientApplication
        # 3. List items in drive: GET /sites/{site_id}/drives/{drive_id}/root/children
        # 4. For each item: GET /sites/{site_id}/drives/{drive_id}/items/{item_id}/content
        # 5. Write content to ADLS raw/{site_id}/{filename}
        # 6. Return DocumentMetadata list

        documents: list[DocumentMetadata] = []
        elapsed = (time.perf_counter() - start) * 1000
        print(
            f"[GraphAPI] pull_id={pull_id} site={site_id} docs={len(documents)} latency={elapsed:.0f}ms"
        )

        return documents

    def _get_graph_endpoint(self) -> str:
        """
        Returns environment-appropriate Graph endpoint. ADR-009.
        commercial: https://graph.microsoft.com
        gcch:       https://graph.microsoft.us
        """
        return self._settings.graph_endpoint
