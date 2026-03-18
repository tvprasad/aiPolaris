# ADR-003: GCCH-Scoped Terraform Workspaces

**Date:** 2026-03-15
**Status:** Accepted

## Context
GCCH access requires organizational validation — personal tenants are not
eligible. The architecture must be deployable to GCCH without redesign.

## Decision
All Azure endpoints are parameterized via Terraform locals toggled by
var.environment = "commercial" | "gcch". Every Azure SDK call reads its
endpoint from settings.py which is populated from Terraform outputs.

## Consequences
- Zero hardcoded endpoints anywhere in application code
- GCCH deployment = terraform workspace select gcch + terraform apply
- Satisfies NIST CM-6 (Configuration Settings) — environment is config, not code
- Demo runs on commercial Azure; production runs on GCCH without code changes

## Interview answer
"GCCH is a workspace variable, not an architecture change. I can show
you the Terraform endpoint matrix right now — every service has both
endpoints defined. Switching environments is one command."
