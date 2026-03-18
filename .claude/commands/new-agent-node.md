# /new-agent-node — Scaffold a new LangGraph agent node

## Usage
/new-agent-node [node name] [description of what it does]

## Instructions
Before generating ANY code, run plan mode first.

Output a plan in this format:
```
Node: [name]
Reads from AgentState: [fields]
Writes to AgentState: [fields]
Must NOT touch: [fields]
Allowed tools: [list or "none"]
CapabilityViolationError conditions: [list]
```

Wait for confirmation that the plan is correct before implementing.

Then generate the node file with this exact structure:

```python
"""
[module path] — [Node name] node.

OWNERSHIP (ADR-004):
  Reads : [fields]
  Writes: [fields]
  Never : [fields]

CAPABILITY (ADR-002):
  allowed_tools: [list or []]
"""

import time
from agent.state import AgentState, StepRecord
from agent.tools.manifests import [MANIFEST], CapabilityViolationError, check_capability


async def [node_name]_node(state: AgentState) -> AgentState:
    """
    [What this node does — one sentence.]
    Appends StepRecord to trace before returning. ADR-004.
    """
    start = time.perf_counter()

    input_summary = {
        # fields this node reads
    }

    # ── Capability check (if tools used) ─────────────────────────────────────
    # check_capability([MANIFEST], tool_name)

    # ── Core logic ────────────────────────────────────────────────────────────
    # TODO: implement

    latency_ms = (time.perf_counter() - start) * 1000

    # ── Append StepRecord — required for all nodes (ADR-004) ─────────────────
    state["trace"].step_log.append(
        StepRecord(
            node_name="[NodeName]",
            input_hash=StepRecord.hash_content(input_summary),
            tool_calls=[],
            output_hash=StepRecord.hash_content({}),
            latency_ms=latency_ms,
        )
    )

    # state["[field]"] = result
    return state
```

Then generate a pytest stub:

```python
# tests/agent/test_[node_name].py
import pytest
from agent.nodes.[node_name] import [node_name]_node
from agent.state import AgentState, TraceContext
from agent.tools.manifests import CapabilityViolationError


def make_state(**kwargs) -> AgentState:
    return AgentState(
        query="test query",
        session_context=None,
        user_oid=None,
        sub_tasks=[],
        retrieved_chunks=[],
        answer="",
        citations=[],
        trace=TraceContext(),
        **kwargs,
    )


@pytest.mark.asyncio
async def test_[node_name]_appends_step_record():
    state = make_state()
    result = await [node_name]_node(state)
    assert len(result["trace"].step_log) == 1
    assert result["trace"].step_log[0].node_name == "[NodeName]"


@pytest.mark.asyncio
async def test_[node_name]_capability_violation():
    # TODO: test that out-of-manifest tool raises CapabilityViolationError
    pass
```

After generating, remind the user to:
1. Add the node to agent/graph.py
2. Add the manifest to agent/tools/manifests.py
3. Update the ownership map comment in agent/state.py
4. Run challenge mode: "Challenge this node's capability enforcement. 3 bypass paths + fixes."
