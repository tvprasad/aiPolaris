# /new-eval-case — Add a golden question to the eval harness

## Usage
/new-eval-case [question] [category] [expected behavior]

## Categories
- direct_factual     — single chunk retrieval, basic RAG quality
- multi_step         — requires synthesizing 2+ chunks
- correct_refusal    — out-of-scope, refusal IS the correct answer
- gap_detection      — should be answerable, refusal = architecture gap to fix
- followup_context   — depends on session context from a prior question

## Instructions
Generate a JSON entry for eval/golden_questions.json:

```json
{
  "id": "q0NN",
  "category": "[category]",
  "question": "[question text]",
  "expected_behavior": "[what a correct answer looks like]",
  "refusal_expected": [true/false],
  "notes": "[why this question tests what it tests — one sentence]"
}
```

Rules:
- id must be sequential — check existing questions for the last id
- refusal_expected: true ONLY for correct_refusal category
- gap_detection questions must have refusal_expected: false
  (refusal here means something is broken, not correct)
- followup_context questions should reference the prior question id in notes

Also check:
- Is there already a similar question? Duplicates dilute the eval signal.
- Does the question require data that hasn't been ingested yet?
  If so, add a note flagging the dependency.

After generating, remind the user to:
1. Add to eval/golden_questions.json
2. Run make eval-smoke to verify the harness still executes
3. If this is a gap_detection case, create a GitHub issue
   tracking the architectural fix it requires
