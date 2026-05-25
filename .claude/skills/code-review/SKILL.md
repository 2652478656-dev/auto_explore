# code-review skill

Compatibility wrapper.

For new work, use:

- `contract-guard` for byte-for-byte baseline contract checks
- `anti-overfit` for benchmark leakage and stale-result checks

This skill exists so older prompts that mention `code-review` still route to the new
audit split.

## Required behavior

When invoked:

1. Run the `contract-guard` checklist.
2. Run the `anti-overfit` checklist.
3. Report blocking issues first.
4. Do not approve a run or keep if either checklist blocks.
