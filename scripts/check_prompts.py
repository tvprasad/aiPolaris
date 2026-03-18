#!/usr/bin/env python3
"""
scripts/check_prompts.py — Prompt integrity check. ADR-008.

Verifies sha256 hashes of all files in agent/prompts/
match the hashes stored in prompts.lock.

Fails with exit code 1 if any file has changed without
a corresponding prompts.lock update.

Run: python scripts/check_prompts.py
     (also runs as pre-commit hook and CI gate)
"""

import hashlib
import json
import sys
from pathlib import Path


PROMPTS_DIR  = Path("agent/prompts")
LOCK_FILE    = Path("prompts.lock")


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if not PROMPTS_DIR.exists():
        print(f"[prompt-integrity] {PROMPTS_DIR} not found — skipping")
        return 0

    prompt_files = sorted(PROMPTS_DIR.glob("*.txt"))
    if not prompt_files:
        print("[prompt-integrity] No prompt files found — skipping")
        return 0

    current_hashes = {f.name: hash_file(f) for f in prompt_files}

    if not LOCK_FILE.exists():
        print("[prompt-integrity] prompts.lock not found — creating")
        LOCK_FILE.write_text(json.dumps(current_hashes, indent=2))
        return 0

    locked_hashes = json.loads(LOCK_FILE.read_text())

    errors = []
    for filename, current_hash in current_hashes.items():
        if filename not in locked_hashes:
            errors.append(f"  NEW: {filename} — add to prompts.lock and create an ADR")
        elif locked_hashes[filename] != current_hash:
            errors.append(f"  CHANGED: {filename} — update prompts.lock and create an ADR (ADR-008)")

    for filename in locked_hashes:
        if filename not in current_hashes:
            errors.append(f"  DELETED: {filename} — remove from prompts.lock")

    if errors:
        print("[prompt-integrity] FAILED — prompt files changed without prompts.lock update:")
        for e in errors:
            print(e)
        print("\nRun: python scripts/update_prompts_lock.py")
        return 1

    print(f"[prompt-integrity] OK — {len(current_hashes)} prompt files verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
