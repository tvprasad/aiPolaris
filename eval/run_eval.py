"""
eval/run_eval.py — Offline eval harness.

Runs all golden questions through the graph.
Records EvalResult per question: answer, confidence, latency, trace_id.
Produces timestamped JSON + markdown summary.

The delta between runs IS the proof of improvement.
Run every day. The trend is the evidence.

Usage:
    make eval                          # full 20-question run
    make eval-smoke                    # 5-question smoke subset
    python eval/run_eval.py --questions eval/golden_questions.json
"""

import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, quantiles


@dataclass
class EvalResult:
    question_id: str
    category: str
    question: str
    answer: str
    confidence: float
    latency_ms: float
    tool_calls: list[str]
    trace_id: str
    refusal: bool
    refusal_expected: bool
    refusal_correct: bool  # True if refusal matches expectation
    timestamp: str


@dataclass
class EvalSummary:
    run_id: str
    question_count: int
    p50_latency_ms: float
    p95_latency_ms: float
    avg_confidence: float
    refusal_rate: float           # total refusals / total questions
    correct_refusal_rate: float   # correct refusals / total questions
    incorrect_refusal_rate: float # incorrect refusals / total questions
    followup_pass_rate: float     # followup_context category pass rate
    results: list[EvalResult]


async def run_question(question: dict) -> EvalResult:
    """
    Run a single golden question through the agent graph.
    Returns EvalResult with all metrics.
    """
    from agent.graph import create_initial_state, graph

    start = time.perf_counter()

    initial_state = create_initial_state(query=question["question"])

    try:
        final_state = await graph.ainvoke(initial_state)
        answer      = final_state.get("answer", "")
        citations   = final_state.get("citations", [])
        trace       = final_state.get("trace")
        tool_calls  = [
            step.tool_calls
            for step in (trace.step_log if trace else [])
        ]
        flat_tools  = [t for sublist in tool_calls for t in sublist]
        confidence  = _estimate_confidence(answer, citations)
        is_refusal  = _is_refusal(answer)

    except Exception as e:
        answer      = f"ERROR: {e}"
        flat_tools  = []
        confidence  = 0.0
        is_refusal  = True
        trace       = None

    latency_ms        = (time.perf_counter() - start) * 1000
    refusal_expected  = question.get("refusal_expected", False)
    refusal_correct   = is_refusal == refusal_expected

    return EvalResult(
        question_id      = question["id"],
        category         = question["category"],
        question         = question["question"],
        answer           = answer,
        confidence       = confidence,
        latency_ms       = round(latency_ms, 2),
        tool_calls       = flat_tools,
        trace_id         = trace.trace_id if trace else "",
        refusal          = is_refusal,
        refusal_expected = refusal_expected,
        refusal_correct  = refusal_correct,
        timestamp        = datetime.now(timezone.utc).isoformat(),
    )


def _is_refusal(answer: str) -> bool:
    refusal_phrases = [
        "don't have enough information",
        "i don't have",
        "not in my knowledge",
        "cannot find",
        "no information available",
    ]
    return any(p in answer.lower() for p in refusal_phrases)


def _estimate_confidence(answer: str, citations: list) -> float:
    """Stub: replace with model confidence score or reranker score."""
    if not answer or _is_refusal(answer):
        return 0.0
    if citations:
        return 0.80
    return 0.60


def compute_summary(run_id: str, results: list[EvalResult]) -> EvalSummary:
    latencies    = [r.latency_ms for r in results]
    sorted_lat   = sorted(latencies)
    n            = len(sorted_lat)
    p50          = sorted_lat[n // 2]
    p95          = sorted_lat[int(n * 0.95)]
    avg_conf     = mean(r.confidence for r in results)

    total          = len(results)
    refusals       = [r for r in results if r.refusal]
    correct_ref    = [r for r in results if r.refusal and r.refusal_correct]
    incorrect_ref  = [r for r in results if r.refusal and not r.refusal_correct]
    followups      = [r for r in results if r.category == "followup_context"]
    fu_pass        = [r for r in followups if not r.refusal] if followups else []

    return EvalSummary(
        run_id                = run_id,
        question_count        = total,
        p50_latency_ms        = round(p50, 2),
        p95_latency_ms        = round(p95, 2),
        avg_confidence        = round(avg_conf, 3),
        refusal_rate          = round(len(refusals) / total, 3),
        correct_refusal_rate  = round(len(correct_ref) / total, 3),
        incorrect_refusal_rate= round(len(incorrect_ref) / total, 3),
        followup_pass_rate    = round(len(fu_pass) / len(followups), 3) if followups else 0.0,
        results               = results,
    )


def write_results(summary: EvalSummary, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"{summary.run_id}.json"
    with open(out_file, "w") as f:
        json.dump(
            {**{k: v for k, v in asdict(summary).items() if k != "results"},
             "results": [asdict(r) for r in summary.results]},
            f, indent=2,
        )
    return out_file


def print_summary(summary: EvalSummary) -> None:
    print(f"\n{'='*60}")
    print(f"Eval run: {summary.run_id}")
    print(f"{'='*60}")
    print(f"Questions      : {summary.question_count}")
    print(f"p50 latency    : {summary.p50_latency_ms:.0f} ms")
    print(f"p95 latency    : {summary.p95_latency_ms:.0f} ms")
    print(f"Avg confidence : {summary.avg_confidence:.2%}")
    print(f"Refusal rate   : {summary.refusal_rate:.2%}  (total)")
    print(f"  Correct       : {summary.correct_refusal_rate:.2%}")
    print(f"  Incorrect     : {summary.incorrect_refusal_rate:.2%}  <- fix target")
    print(f"Follow-up pass : {summary.followup_pass_rate:.2%}")
    print(f"{'='*60}\n")


async def main(questions_file: str) -> None:
    run_id = datetime.now(timezone.utc).strftime("eval_%Y%m%dT%H%M%SZ")

    with open(questions_file) as f:
        questions = json.load(f)

    print(f"Running {len(questions)} questions (run_id={run_id})...")
    results = await asyncio.gather(*[run_question(q) for q in questions])

    summary  = compute_summary(run_id, list(results))
    out_file = write_results(summary, Path("eval/results"))
    print_summary(summary)
    print(f"Results written to {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", default="eval/golden_questions.json")
    args = parser.parse_args()
    asyncio.run(main(args.questions))
