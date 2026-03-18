# /gcch-check — Scan for hardcoded commercial Azure endpoints

## Usage
/gcch-check [file or paste code]

## Instructions
Scan the provided code for any hardcoded Azure commercial endpoint strings.

Check for these patterns:
- *.openai.azure.com
- *.search.windows.net
- graph.microsoft.com
- *.vault.azure.net
- *.dfs.core.windows.net
- *.blob.core.windows.net
- login.microsoftonline.com
- management.azure.com
- Any string containing "azure.com" that isn't in a comment

For each finding, output:

```
FINDING: [line number or location]
Current : [the hardcoded value]
Fix     : Use settings.[field_name] instead
GCCH eq : [what it would be in GCCH — *.azure.us equivalent]
ADR     : ADR-009 violation
NIST    : CM-6 — Configuration Settings
```

If no findings:
```
GCCH CHECK PASSED — no hardcoded commercial endpoints found.
All Azure endpoints appear to be read from settings.py.
```

After scanning, remind the user:
- Every Azure endpoint must come from settings.py
- settings.py is populated from Terraform outputs at deploy time
- The /gcch-check pre-commit hook runs this automatically on every commit
- Run: make tf-plan env=gcch to verify the GCCH workspace is valid
