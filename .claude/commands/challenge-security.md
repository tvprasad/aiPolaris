# /challenge-security — Adversarial review of security-critical code

## Usage
/challenge-security [paste the implementation to challenge]

## When to use
Run this after implementing ANY of:
- Tool manifest enforcement (CapabilityViolationError)
- Entra ID token validation
- RBAC middleware
- Key Vault credential fetching
- Any auth or permission boundary

## Instructions
You are a security adversary trying to bypass the implementation.
Find exactly 3 bypass paths. For each:

```
BYPASS [N]: [name — 2-4 words]
Attack path: [how an attacker or misconfigured agent exploits this — 2 sentences]
Severity   : CRITICAL | HIGH | MEDIUM
NIST impact: [which control this violates]
Fix        : [exact code change that closes this bypass]
```

Focus on these bypass categories:
1. Manifest misconfiguration — wrong key name, missing field, default value exploited
2. State mutation side-effect — node writes field it shouldn't own, corrupting downstream
3. Token validation gap — missing check (signature? expiry? audience? issuer?)
4. Injection via user input — query crafted to override system behavior
5. Race condition — concurrent requests sharing mutable state
6. Terraform misconfiguration — commercial endpoint in GCCH workspace

After findings, output:

```
CHALLENGE SUMMARY
Bypasses found : [N]
Critical       : [N]
Recommendation : [one sentence — what to fix first]
```

Remind the user:
- All CRITICAL findings must be fixed before merging
- Add a rule to CLAUDE.md for each finding pattern
- Re-run /challenge-security after fixes to verify closure
- Document findings in the PR description
