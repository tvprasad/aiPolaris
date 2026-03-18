## Summary
<!-- What does this PR do? One sentence. -->

## Type
- [ ] Feature
- [ ] Bug fix
- [ ] Security fix
- [ ] ADR update
- [ ] Infrastructure / Terraform
- [ ] Eval harness update
- [ ] Documentation

## ADR compliance
<!-- List any ADRs this PR touches or satisfies -->
- [ ] No ADR changes required
- [ ] ADR created / updated: ADR-NNN — [title]
- [ ] CLAUDE.md updated with new constraint

## Security checklist
<!-- Run /challenge-security on any security-critical changes -->
- [ ] No hardcoded Azure endpoints (ADR-009 / /gcch-check passed)
- [ ] No credentials in code (Key Vault only, ADR-003)
- [ ] RBAC check in middleware, not route handler
- [ ] CapabilityViolationError enforced on any new tool call
- [ ] Challenge mode run on security-critical changes: [ ] findings resolved

## State ownership (agent changes only)
- [ ] Node reads only its declared fields
- [ ] Node writes only its declared fields
- [ ] StepRecord appended before returning
- [ ] Ownership map updated in agent/state.py

## Test coverage
- [ ] Unit tests added / updated
- [ ] Coverage ≥ 80% (CI will verify)
- [ ] CapabilityViolationError test exists for any new tool manifest

## Eval impact
- [ ] No eval impact
- [ ] Eval run before merge: p95=___ms, incorrect_refusal=___%, confidence=___%
- [ ] Golden question added/updated in golden_questions.json

## GCCH readiness
- [ ] /gcch-check passed — no hardcoded commercial endpoints
- [ ] Terraform plan verified: make tf-plan env=gcch

## Release record
<!-- Filled automatically by CI on merge to main -->
- Release record will be generated automatically on merge

## Notes for reviewer
<!-- Anything the reviewer needs to know -->
