# /new-adr — Generate a new Architecture Decision Record

## Usage
/new-adr [decision description]

## Instructions
Generate a complete ADR from the decision description provided.

Use this exact structure:

```markdown
# ADR-NNN: [Decision Title]

**Date:** [today]
**Status:** Accepted
**Project:** [project name from CLAUDE.md]

## Context
[Why this decision needs to be made. What forces are at play.
What the system requires. What compliance constraints apply.]

## Options Considered

### Option A: [name] (selected / rejected)
- [key characteristic]
- [federal/compliance implication]

### Option B: [name] (rejected)
- [key characteristic]
- [why rejected]

### Option C: [name] (rejected)
- [key characteristic]
- [why rejected]

## Decision
**[Selected option].** [One sentence explaining why — the most important reason.]

## Consequences

**Positive:**
- [outcome 1]
- [outcome 2]

**Negative / tradeoffs:**
- [tradeoff 1]

**GCCH implications:**
- [how this decision affects GCCH deployment]

## NIST mapping
[Control ID]: [why this ADR satisfies it]

## Interview answer
"[1-3 sentence answer to 'why did you choose X over Y?' that a
technical director would find credible and specific.]"
```

After generating, remind the user to:
1. Number it sequentially (check docs/adr/ for the last ADR number)
2. Add the constraint to CLAUDE.md under ADR constraints
3. Update the ADR table in README.md
