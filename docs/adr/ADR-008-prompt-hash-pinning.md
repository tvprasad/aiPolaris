# ADR-008: Prompt Hash-Pinning via prompts.lock

**Date:** 2026-03-15
**Status:** Accepted

## Context
Prompt changes silently alter system behavior — a compliance risk under
NIST CM-3 (Configuration Change Control). Without pinning, a prompt edit
can change agent behavior without triggering a deployment review.

## Decision
All prompt templates live in agent/prompts/.
prompts.lock stores sha256 of every file in agent/prompts/.
Pre-commit hook (prompt-integrity) fails if any prompt file changes
without a corresponding prompts.lock update + ADR bump.
Release record includes all prompt hashes.

## Consequences
- Prompt changes are tracked with the same rigor as code changes
- Satisfies NIST CM-3 (Configuration Change Control) and SA-10
- Deterministic execution: same prompt + pinned model = same output

## Interview answer
"Prompts are version-controlled with hash-pinning. A prompt change
without an ADR bump fails the pre-commit hook. The release record
includes every prompt hash — the compliance trail is complete."
