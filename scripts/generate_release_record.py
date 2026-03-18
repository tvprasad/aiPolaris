#!/usr/bin/env python3
"""
scripts/generate_release_record.py — Immutable ATO evidence artifact.

Generates a YAML release record on every main merge.
Never edited. Appended only. Every field maps to a NIST 800-53 control.

Usage:
    python scripts/generate_release_record.py
    make release-record

Environment variables (set by CI):
    GIT_SHA, DEPLOYED_BY, ENVIRONMENT
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


PROMPTS_DIR   = Path("agent/prompts")
LOCK_FILE     = Path("prompts.lock")
RECORDS_DIR   = Path("release_records")
EVAL_RESULTS  = Path("eval/results")


def get_git_sha() -> str:
    return os.getenv("GIT_SHA") or subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()


def get_prompt_hashes() -> dict:
    if not LOCK_FILE.exists():
        return {}
    return json.loads(LOCK_FILE.read_text())


def get_latest_eval() -> dict:
    if not EVAL_RESULTS.exists():
        return {}
    results = sorted(EVAL_RESULTS.glob("*.json"))
    if not results:
        return {}
    latest = json.loads(results[-1].read_text())
    return {
        "run_id":                  latest.get("run_id", ""),
        "p50_latency_ms":          latest.get("p50_latency_ms", 0),
        "p95_latency_ms":          latest.get("p95_latency_ms", 0),
        "avg_confidence":          latest.get("avg_confidence", 0),
        "refusal_rate":            latest.get("refusal_rate", 0),
        "incorrect_refusal_rate":  latest.get("incorrect_refusal_rate", 0),
        "followup_pass_rate":      latest.get("followup_pass_rate", 0),
    }


def main() -> int:
    RECORDS_DIR.mkdir(exist_ok=True)

    now       = datetime.now(timezone.utc)
    sha       = get_git_sha()
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    filename  = f"{timestamp}_{sha[:8]}.yaml"

    record = {
        "release_id":    timestamp,
        "git_sha":       sha,
        "deployed_by":   os.getenv("DEPLOYED_BY", "local"),
        "environment":   os.getenv("ENVIRONMENT", "commercial"),

        # Security gates — all must be true (set by CI environment)
        "sast_passed":            os.getenv("SAST_PASSED", "false") == "true",
        "dependency_scan_clean":  os.getenv("DEPS_CLEAN",  "false") == "true",
        "secrets_scan_clean":     os.getenv("SECRETS_CLEAN","false") == "true",
        "type_check_passed":      os.getenv("TYPES_PASSED", "false") == "true",
        "test_coverage_pct":      float(os.getenv("COVERAGE_PCT", "0")),

        # Prompt integrity — ADR-008 / NIST CM-3
        "prompt_hashes": get_prompt_hashes(),

        # Eval delta — behavioral ConMon / NIST CA-7
        "eval": get_latest_eval(),

        # Infrastructure — ADR-009 / NIST CM-3
        "terraform_workspace":   os.getenv("ENVIRONMENT", "commercial"),
        "confidence_threshold":  0.60,
    }

    out_path = RECORDS_DIR / filename
    with open(out_path, "w") as f:
        yaml.dump(record, f, default_flow_style=False, sort_keys=False)

    print(f"Release record written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
