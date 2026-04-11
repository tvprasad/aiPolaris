"""
scripts/check_eval_thresholds.py — CI eval-smoke gate.

Reads the most recent eval results JSON from eval/results/ and asserts
that behavioral metrics stay within the specified bounds.

Usage (from CI):
    python scripts/check_eval_thresholds.py \
        --max-incorrect-refusal 0.40 \
        --max-p95-latency 30000

Exits non-zero on violation so CI fails the eval-smoke job.
"""

import argparse
import json
import sys
from pathlib import Path


def latest_results_file(results_dir: Path) -> Path | None:
    files = sorted(results_dir.glob("eval_*.json"), key=lambda f: f.stat().st_mtime)
    return files[-1] if files else None


def check_thresholds(
    results_path: Path,
    max_incorrect_refusal: float,
    max_p95_latency: float,
) -> list[str]:
    """Return a list of violation messages. Empty list = all passing."""
    with open(results_path) as f:
        data = json.load(f)

    violations: list[str] = []

    incorrect_refusal_rate: float = data.get("incorrect_refusal_rate", 0.0)
    p95_latency_ms: float = data.get("p95_latency_ms", 0.0)

    if incorrect_refusal_rate > max_incorrect_refusal:
        violations.append(
            f"FAIL incorrect_refusal_rate={incorrect_refusal_rate:.3f} "
            f"exceeds max={max_incorrect_refusal:.3f}"
        )

    if p95_latency_ms > max_p95_latency:
        violations.append(
            f"FAIL p95_latency_ms={p95_latency_ms:.0f} "
            f"exceeds max={max_p95_latency:.0f}ms"
        )

    return violations


def main() -> None:
    parser = argparse.ArgumentParser(description="Eval threshold gate for CI")
    parser.add_argument(
        "--max-incorrect-refusal",
        type=float,
        default=0.40,
        help="Maximum acceptable incorrect_refusal_rate (0–1)",
    )
    parser.add_argument(
        "--max-p95-latency",
        type=float,
        default=30_000,
        help="Maximum acceptable p95 latency in ms",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("eval/results"),
        help="Directory containing eval result JSON files",
    )
    args = parser.parse_args()

    results_dir: Path = args.results_dir

    if not results_dir.exists():
        print(f"ERROR eval/results/ directory not found at {results_dir}")
        sys.exit(1)

    results_file = latest_results_file(results_dir)
    if results_file is None:
        print(f"ERROR no eval result files found in {results_dir}")
        sys.exit(1)

    print(f"Checking thresholds against: {results_file.name}")

    violations = check_thresholds(
        results_path=results_file,
        max_incorrect_refusal=args.max_incorrect_refusal,
        max_p95_latency=args.max_p95_latency,
    )

    if violations:
        print("\nThreshold violations:")
        for v in violations:
            print(f"  {v}")
        print(f"\nEval gate FAILED — {len(violations)} violation(s)")
        sys.exit(1)
    else:
        print("All eval thresholds passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
