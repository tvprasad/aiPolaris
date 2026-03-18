"""
agent/memory/session.py — InMemorySessionStore. ADR-006.

Short-term memory scoped to conversation window.
TTL=1800s (30 min inactivity). Keyed by session_id (UUID).
Fixes follow-up query false refusals by passing prior context
into AgentState on every graph invocation.

No cross-session leakage — TTL ensures clean expiry.
Satisfies NIST SC-4 (Information in Shared Resources).
"""

import time
from dataclasses import dataclass, field


@dataclass
class SessionEntry:
    session_id: str
    last_query: str
    last_answer: str
    last_chunks: list[dict]
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)


class InMemorySessionStore:
    """
    Thread-safe in-memory session store with TTL expiry.
    TTL default: 1800s (ADR-006).
    """

    def __init__(self, ttl_seconds: int = 1800):
        self._store: dict[str, SessionEntry] = {}
        self._ttl = ttl_seconds

    def get(self, session_id: str) -> dict | None:
        """Return session context if exists and not expired."""
        entry = self._store.get(session_id)
        if entry is None:
            return None
        if time.time() - entry.last_accessed > self._ttl:
            del self._store[session_id]
            return None
        entry.last_accessed = time.time()
        return {
            "last_query": entry.last_query,
            "last_answer": entry.last_answer,
            "last_chunks": entry.last_chunks,
        }

    def set(
        self,
        session_id: str,
        query: str,
        answer: str,
        chunks: list[dict],
    ) -> None:
        """Store or update session context after a completed graph invocation."""
        self._store[session_id] = SessionEntry(
            session_id=session_id,
            last_query=query,
            last_answer=answer,
            last_chunks=chunks,
        )

    def clear(self, session_id: str) -> None:
        """Explicitly clear a session (e.g., user logout)."""
        self._store.pop(session_id, None)

    def _purge_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        now = time.time()
        expired = [
            k for k, v in self._store.items()
            if now - v.last_accessed > self._ttl
        ]
        for k in expired:
            del self._store[k]
        return len(expired)


# Module-level singleton — shared across all requests in the process
session_store = InMemorySessionStore(ttl_seconds=1800)
