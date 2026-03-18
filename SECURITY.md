# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | Yes                |

## Reporting a Vulnerability

If you discover a security vulnerability in aiPolaris, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, email: **security@vplsolutions.com**

Please include:
- Description of the vulnerability
- Steps to reproduce
- Impact assessment
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a timeline for resolution.

## Security Design Principles

aiPolaris enforces security at the architecture level:

- **Default-deny capability sandboxing** -- every agent node has a declared tool manifest. Any out-of-manifest call raises `CapabilityViolationError`.
- **No credentials in code** -- all secrets via Azure Key Vault with managed identity.
- **Entra ID authentication** -- every request validated for signature, expiry, audience, and issuer.
- **RBAC in middleware only** -- never in route handlers.
- **Read-only agents by default** -- per ADR-002.
- **Audit trail** -- TraceContext with trace_id and StepRecord per node (ADR-004).
