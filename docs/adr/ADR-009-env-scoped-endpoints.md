# ADR-009: Environment-Scoped Azure Endpoints

**Date:** 2026-03-15
**Status:** Accepted

## Context
Commercial Azure and GCCH use different endpoint domains. Hardcoded
endpoints make GCCH deployment require code changes — an architecture
defect that would fail an ATO review.

## Decision
All Azure endpoints defined as Terraform locals in infra/terraform/settings.tf.
Toggled by var.environment = "commercial" | "gcch".
Application code reads ALL endpoints from settings.py (populated from
Terraform outputs at deploy time). Zero hardcoded URLs in application code.

## Consequences
- GCCH migration = terraform workspace select gcch && terraform apply
- Satisfies NIST CM-6 — environment is configuration, not code
- Any hardcoded endpoint is caught by /gcch-check skill and CI gate

## Interview answer
"Every Azure endpoint is a Terraform local parameterized by environment.
The application has zero hardcoded URLs. GCCH deployment is a workspace
switch — the architecture doesn't change."
