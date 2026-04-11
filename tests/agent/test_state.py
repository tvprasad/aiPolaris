"""
tests/agent/test_state.py — Unit tests for AgentState, TraceContext, StepRecord.
"""

import uuid

from agent.state import AgentState, StepRecord, TraceContext


class TestStepRecordHashContent:
    def test_consistent_hash_for_same_input(self) -> None:
        h1 = StepRecord.hash_content({"key": "value"})
        h2 = StepRecord.hash_content({"key": "value"})
        assert h1 == h2

    def test_different_hash_for_different_input(self) -> None:
        h1 = StepRecord.hash_content({"key": "a"})
        h2 = StepRecord.hash_content({"key": "b"})
        assert h1 != h2

    def test_hash_is_16_char_hex(self) -> None:
        h = StepRecord.hash_content("anything")
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_sort_keys_makes_order_irrelevant(self) -> None:
        h1 = StepRecord.hash_content({"a": 1, "b": 2})
        h2 = StepRecord.hash_content({"b": 2, "a": 1})
        assert h1 == h2

    def test_handles_nested_and_list_content(self) -> None:
        content = {"nodes": ["planner", "retriever"], "count": 2}
        h = StepRecord.hash_content(content)
        assert len(h) == 16


class TestStepRecord:
    def test_fields_stored_correctly(self) -> None:
        record = StepRecord(
            node_name="Planner",
            input_hash="abc123",
            tool_calls=[],
            output_hash="def456",
            latency_ms=42.5,
        )
        assert record.node_name == "Planner"
        assert record.input_hash == "abc123"
        assert record.tool_calls == []
        assert record.output_hash == "def456"
        assert record.latency_ms == 42.5

    def test_timestamp_is_set_automatically(self) -> None:
        record = StepRecord(
            node_name="Retriever",
            input_hash="x",
            tool_calls=["ai_search_read"],
            output_hash="y",
            latency_ms=10.0,
        )
        assert record.timestamp  # non-empty string
        assert "T" in record.timestamp  # ISO format

    def test_tool_calls_preserved(self) -> None:
        record = StepRecord(
            node_name="Retriever",
            input_hash="x",
            tool_calls=["ai_search_read"],
            output_hash="y",
            latency_ms=5.0,
        )
        assert record.tool_calls == ["ai_search_read"]


class TestTraceContext:
    def test_trace_id_is_valid_uuid(self) -> None:
        tc = TraceContext()
        parsed = uuid.UUID(tc.trace_id)
        assert str(parsed) == tc.trace_id

    def test_two_instances_have_different_trace_ids(self) -> None:
        tc1 = TraceContext()
        tc2 = TraceContext()
        assert tc1.trace_id != tc2.trace_id

    def test_step_log_starts_empty(self) -> None:
        tc = TraceContext()
        assert tc.step_log == []

    def test_to_dict_contains_trace_id(self) -> None:
        tc = TraceContext()
        d = tc.to_dict()
        assert d["trace_id"] == tc.trace_id

    def test_to_dict_empty_steps(self) -> None:
        tc = TraceContext()
        d = tc.to_dict()
        assert d["steps"] == []

    def test_to_dict_with_step_record(self) -> None:
        tc = TraceContext()
        record = StepRecord(
            node_name="Synthesizer",
            input_hash="aaa",
            tool_calls=[],
            output_hash="bbb",
            latency_ms=123.45,
        )
        tc.step_log.append(record)
        d = tc.to_dict()
        assert len(d["steps"]) == 1
        step = d["steps"][0]
        assert step["node"] == "Synthesizer"
        assert step["input_hash"] == "aaa"
        assert step["output_hash"] == "bbb"
        assert step["latency_ms"] == 123.45
        assert step["tool_calls"] == []
        assert "timestamp" in step

    def test_to_dict_rounds_latency(self) -> None:
        tc = TraceContext()
        record = StepRecord(
            node_name="Planner",
            input_hash="x",
            tool_calls=[],
            output_hash="y",
            latency_ms=99.9999,
        )
        tc.step_log.append(record)
        d = tc.to_dict()
        assert d["steps"][0]["latency_ms"] == round(99.9999, 2)


class TestAgentState:
    def test_agent_state_can_be_constructed_as_typed_dict(self) -> None:
        state = AgentState(
            query="What is the policy?",
            session_context=None,
            user_oid=None,
            sub_tasks=[],
            retrieved_chunks=[],
            answer="",
            citations=[],
            trace=TraceContext(),
        )
        assert state["query"] == "What is the policy?"
        assert state["sub_tasks"] == []
        assert state["answer"] == ""

    def test_state_fields_are_mutable(self) -> None:
        tc = TraceContext()
        state = AgentState(
            query="q",
            session_context=None,
            user_oid="oid-123",
            sub_tasks=[],
            retrieved_chunks=[],
            answer="",
            citations=[],
            trace=tc,
        )
        state["sub_tasks"] = ["task1", "task2"]
        assert state["sub_tasks"] == ["task1", "task2"]

    def test_state_trace_is_trace_context(self) -> None:
        tc = TraceContext()
        state = AgentState(
            query="q",
            session_context=None,
            user_oid=None,
            sub_tasks=[],
            retrieved_chunks=[],
            answer="",
            citations=[],
            trace=tc,
        )
        assert isinstance(state["trace"], TraceContext)
