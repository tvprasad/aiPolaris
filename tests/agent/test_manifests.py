"""
tests/agent/test_manifests.py — Unit tests for tool manifests and CapabilityViolationError.
"""

import pytest

from agent.tools.manifests import (
    PLANNER_MANIFEST,
    RETRIEVER_MANIFEST,
    SYNTHESIZER_MANIFEST,
    CapabilityViolationError,
    check_capability,
)


class TestCapabilityViolationError:
    def test_is_exception_subclass(self) -> None:
        assert issubclass(CapabilityViolationError, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(CapabilityViolationError):
            raise CapabilityViolationError("test violation")

    def test_message_preserved(self) -> None:
        with pytest.raises(CapabilityViolationError, match="test violation"):
            raise CapabilityViolationError("test violation")


class TestCheckCapability:
    def test_raises_for_denied_tool_on_planner(self) -> None:
        with pytest.raises(CapabilityViolationError):
            check_capability(PLANNER_MANIFEST, "ai_search_read")

    def test_raises_for_denied_tool_on_synthesizer(self) -> None:
        with pytest.raises(CapabilityViolationError):
            check_capability(SYNTHESIZER_MANIFEST, "ai_search_read")

    def test_passes_for_allowed_tool_on_retriever(self) -> None:
        # Should not raise
        check_capability(RETRIEVER_MANIFEST, "ai_search_read")

    def test_raises_for_disallowed_tool_on_retriever(self) -> None:
        with pytest.raises(CapabilityViolationError):
            check_capability(RETRIEVER_MANIFEST, "graph_api_write")

    def test_error_message_includes_node_name(self) -> None:
        with pytest.raises(CapabilityViolationError, match="Planner"):
            check_capability(PLANNER_MANIFEST, "some_tool")

    def test_error_message_includes_tool_name(self) -> None:
        with pytest.raises(CapabilityViolationError, match="some_tool"):
            check_capability(PLANNER_MANIFEST, "some_tool")

    def test_error_message_includes_allowed_list(self) -> None:
        with pytest.raises(CapabilityViolationError, match="none"):
            check_capability(PLANNER_MANIFEST, "any_tool")


class TestManifestDefinitions:
    def test_planner_has_no_allowed_tools(self) -> None:
        assert PLANNER_MANIFEST["allowed_tools"] == []

    def test_synthesizer_has_no_allowed_tools(self) -> None:
        assert SYNTHESIZER_MANIFEST["allowed_tools"] == []

    def test_retriever_allows_ai_search_read(self) -> None:
        assert "ai_search_read" in RETRIEVER_MANIFEST["allowed_tools"]

    def test_retriever_does_not_allow_writes(self) -> None:
        assert "ai_search_write" not in RETRIEVER_MANIFEST["allowed_tools"]

    def test_planner_node_name(self) -> None:
        assert PLANNER_MANIFEST["node_name"] == "Planner"

    def test_retriever_node_name(self) -> None:
        assert RETRIEVER_MANIFEST["node_name"] == "Retriever"

    def test_synthesizer_node_name(self) -> None:
        assert SYNTHESIZER_MANIFEST["node_name"] == "Synthesizer"

    def test_all_manifests_have_denied_reason(self) -> None:
        for manifest in (PLANNER_MANIFEST, RETRIEVER_MANIFEST, SYNTHESIZER_MANIFEST):
            assert manifest["denied_reason"]
