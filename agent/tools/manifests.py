"""
agent/tools/manifests.py — Scoped tool manifests per agent node.

Each node has an explicit allowed_tools list. Any call to a tool
not in allowed_tools raises CapabilityViolationError. ADR-002.

NIST AC-6: Least Privilege — agents never have more capability
than their task requires.
"""

from typing import TypedDict


class ToolManifest(TypedDict):
    node_name: str
    allowed_tools: list[str]
    denied_reason: str  # why all other tools are denied


class CapabilityViolationError(Exception):
    """
    Raised when a node attempts a tool call outside its manifest.
    This is a security control, not just a runtime error. ADR-002.

    Usage:
        if tool_name not in manifest["allowed_tools"]:
            raise CapabilityViolationError(
                f"{manifest['node_name']} attempted '{tool_name}'. "
                f"Allowed: {manifest['allowed_tools']}"
            )
    """
    pass


# ── Node manifests ────────────────────────────────────────────────────────────

PLANNER_MANIFEST: ToolManifest = {
    "node_name": "Planner",
    "allowed_tools": [],  # no tool access — decomposes query only
    "denied_reason": (
        "Planner decomposes the query into sub-tasks using only the "
        "query text and session context. It has no data access by design. "
        "Data access is Retriever's responsibility."
    ),
}

RETRIEVER_MANIFEST: ToolManifest = {
    "node_name": "Retriever",
    "allowed_tools": ["ai_search_read"],  # read-only, no writes ever
    "denied_reason": (
        "Retriever may only read from the AI Search index. "
        "Write operations, Graph API calls, and credential access "
        "are denied. ADR-002: read-only by default."
    ),
}

SYNTHESIZER_MANIFEST: ToolManifest = {
    "node_name": "Synthesizer",
    "allowed_tools": [],  # operates on state only — no external calls
    "denied_reason": (
        "Synthesizer assembles the answer from already-retrieved chunks "
        "in state. It has no external tool access — all data it needs "
        "was placed in state by the Retriever."
    ),
}


def check_capability(manifest: ToolManifest, tool_name: str) -> None:
    """
    Enforce tool manifest. Call before every tool invocation.
    Raises CapabilityViolationError if tool_name is not allowed.
    """
    if tool_name not in manifest["allowed_tools"]:
        raise CapabilityViolationError(
            f"[{manifest['node_name']}] attempted tool '{tool_name}'. "
            f"Allowed tools: {manifest['allowed_tools'] or 'none'}. "
            f"Reason denied: {manifest['denied_reason']}"
        )
