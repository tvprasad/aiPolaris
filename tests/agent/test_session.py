"""
tests/agent/test_session.py — Unit tests for InMemorySessionStore. ADR-006.
"""

from unittest.mock import patch

import pytest

from agent.memory.session import InMemorySessionStore


@pytest.fixture
def store() -> InMemorySessionStore:
    return InMemorySessionStore(ttl_seconds=1800)


class TestGet:
    def test_returns_none_for_unknown_session(self, store: InMemorySessionStore) -> None:
        assert store.get("nonexistent-id") is None

    def test_returns_stored_context_after_set(self, store: InMemorySessionStore) -> None:
        store.set("s1", "what is policy?", "The policy is X.", [{"chunk": "a"}])
        result = store.get("s1")
        assert result is not None
        assert result["last_query"] == "what is policy?"
        assert result["last_answer"] == "The policy is X."
        assert result["last_chunks"] == [{"chunk": "a"}]

    def test_returns_none_after_ttl_expired(self, store: InMemorySessionStore) -> None:
        store.set("s2", "query", "answer", [])
        # Advance time past TTL
        with patch("agent.memory.session.time.time", return_value=9999999999.0):
            result = store.get("s2")
        assert result is None

    def test_expired_entry_is_deleted_from_store(self, store: InMemorySessionStore) -> None:
        store.set("s3", "q", "a", [])
        with patch("agent.memory.session.time.time", return_value=9999999999.0):
            store.get("s3")
        # After expiry get, the entry must be gone
        assert store.get("s3") is None

    def test_updates_last_accessed_on_hit(self, store: InMemorySessionStore) -> None:
        store.set("s4", "q", "a", [])
        entry_before = store._store["s4"].last_accessed
        with patch("agent.memory.session.time.time", return_value=entry_before + 100):
            store.get("s4")
        assert store._store["s4"].last_accessed >= entry_before + 100


class TestSet:
    def test_overwrites_existing_session(self, store: InMemorySessionStore) -> None:
        store.set("s5", "q1", "a1", [])
        store.set("s5", "q2", "a2", [{"x": 1}])
        result = store.get("s5")
        assert result is not None
        assert result["last_query"] == "q2"
        assert result["last_answer"] == "a2"

    def test_stores_empty_chunks(self, store: InMemorySessionStore) -> None:
        store.set("s6", "q", "a", [])
        result = store.get("s6")
        assert result is not None
        assert result["last_chunks"] == []


class TestClear:
    def test_clear_removes_session(self, store: InMemorySessionStore) -> None:
        store.set("s7", "q", "a", [])
        store.clear("s7")
        assert store.get("s7") is None

    def test_clear_nonexistent_session_is_safe(self, store: InMemorySessionStore) -> None:
        store.clear("does-not-exist")  # Should not raise


class TestPurgeExpired:
    def test_purge_removes_expired_entries(self, store: InMemorySessionStore) -> None:
        store.set("e1", "q", "a", [])
        store.set("e2", "q", "a", [])
        with patch("agent.memory.session.time.time", return_value=9999999999.0):
            count = store._purge_expired()
        assert count == 2
        assert "e1" not in store._store
        assert "e2" not in store._store

    def test_purge_keeps_fresh_entries(self, store: InMemorySessionStore) -> None:
        store.set("fresh", "q", "a", [])
        count = store._purge_expired()
        assert count == 0
        assert "fresh" in store._store

    def test_purge_returns_zero_when_empty(self, store: InMemorySessionStore) -> None:
        assert store._purge_expired() == 0


class TestNoSessionLeakage:
    def test_two_sessions_independent(self, store: InMemorySessionStore) -> None:
        store.set("user-a", "query A", "answer A", [{"a": 1}])
        store.set("user-b", "query B", "answer B", [{"b": 2}])

        result_a = store.get("user-a")
        result_b = store.get("user-b")

        assert result_a is not None
        assert result_b is not None
        assert result_a["last_query"] == "query A"
        assert result_b["last_query"] == "query B"
        assert result_a["last_chunks"] == [{"a": 1}]
        assert result_b["last_chunks"] == [{"b": 2}]
