# anti-overfit skill

Use this skill before every run and before keeping any result.

The fixed 100-row benchmark makes leakage tempting. This skill treats benchmark gaming
as a correctness failure, even when cosine passes.

## Hard blocks

Block if implementation:

- reads or copies `baseline_output.npy`
- uses cosine output to tune runtime behavior
- branches on benchmark row identity, language, file path, row count, sample seed, or
  metadata
- caches embeddings keyed by current inputs
- reuses previous `result.npy`
- generates synthetic vectors instead of model embeddings
- excludes required GPU work from elapsed timing

## Freshness checks

Check:

- `result.npy` modification time is after run start
- log corresponds to current commit
- output shape matches baseline
- throughput line exists exactly once unless rerun is documented

## Information separation

Prefer this flow:

- implementer sees hypothesis and code context
- orchestrator sees full score history
- overfit/reviewer agents see score history only during audit

This reduces accidental benchmark-fitting through repeated score feedback.
