#!/usr/bin/env python3
"""
scripts/update_prompts_lock.py — Regenerate prompts.lock. ADR-008.

Run this after intentionally changing a prompt file.
An ADR bump is required alongside any prompt change — this script
does not enforce that, but CI will fail without it.

Usage:
    python scripts/update_prompts_lock.py
    make update-prompts-lock
"""

import hashlib
import json
import sys
from pathlib import Path

PROMPTS_DIR = Path("agent/prompts")
LOCK_FILE = Path("prompts.lock")


def main() -> int:
    prompt_files = sorted(PROMPTS_DIR.glob("*.txt"))
    if not prompt_files:
        print("[prompt-integrity] No prompt files found.")
        return 1

    hashes = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in prompt_files}
    LOCK_FILE.write_text(json.dumps(hashes, indent=2))
    print(f"[prompt-integrity] prompts.lock updated — {len(hashes)} files hashed.")
    for name, h in hashes.items():
        print(f"  {name}: {h[:12]}...")
    print("\nReminder: create or update an ADR before committing (ADR-008).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
