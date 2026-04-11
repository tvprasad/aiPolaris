"""
agent/state.py — AgentState schema, TraceContext, and StepRecord.

OWNERSHIP MAP (ADR-004):
  Planner    : reads query, session_context | writes sub_tasks
  Retriever  : reads sub_tasks              | writes retrieved_chunks
  Synthesizer: reads retrieved_chunks       | writes answer, citations
  All nodes  : append to trace.step_log     | never modify other fields

All nodes append a StepRecord before returning. This is enforced by
the CLAUDE.md ML Engineer mode rules and tested in tests/agent/.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypedDict


@dataclass
class StepRecord:
    """Immutable record of a single agent node execution. ADR-004."""

    node_name: str
    input_hash: str  # sha256 of serialized node inputs
    tool_calls: list[str]  # names of tools actually called ([] if none)
    output_hash: str  # sha256 of serialized node outputs
    latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @staticmethod
    def hash_content(content: Any) -> str:
        """Produce a stable sha256 hash of any JSON-serializable content."""
        serialized = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]


@dataclass
class TraceContext:
    """
    Full execution trace for one graph invocation.
    trace_id ties every log entry, audit record, and release artifact
    back to a single deterministic execution unit. ADR-004.
    """

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    step_log: list[StepRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "steps": [
                {
                    "node": s.node_name,
                    "input_hash": s.input_hash,
                    "tool_calls": s.tool_calls,
                    "output_hash": s.output_hash,
                    "latency_ms": round(s.latency_ms, 2),
                    "timestamp": s.timestamp,
                }
                for s in self.step_log
            ],
        }


class AgentState(TypedDict):
    """
    Shared state passed through the LangGraph DAG.

    Field ownership (ADR-004) — nodes must only write their declared fields:
      query            : set at graph entry, read-only for all nodes
      sub_tasks        : written by Planner only
      retrieved_chunks : written by Retriever only
      answer           : written by Synthesizer only
      citations        : written by Synthesizer only
      trace            : all nodes append to step_log, never replace
      session_context  : set at graph entry from SessionStore, read-only
      user_oid         : set at graph entry from Entra ID token, read-only
    """

    # Input
    query: str
    session_context: dict[str, object] | None  # from InMemorySessionStore (ADR-006)
    user_oid: str | None  # from Entra ID token (auth middleware)

    # Planner output
    sub_tasks: list[str]

    # Retriever output
    retrieved_chunks: list[dict[str, object]]

    # Synthesizer output
    answer: str
    citations: list[dict[str, object]]

    # Trace — all nodes append, never replace (ADR-004)
    trace: TraceContext
