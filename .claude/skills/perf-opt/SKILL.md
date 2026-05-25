# perf-opt skill

Compatibility wrapper.

For new work, use:

- `experiment-design` to define the hypothesis and enforce diversity
- `perf-patterns` to generate concrete optimization mechanisms

This skill exists only so older prompts that mention `perf-opt` still route to the new
two-part process.

## Required behavior

When invoked:

1. Generate or select a mechanism using `perf-patterns`.
2. Write the hypothesis using `experiment-design`.
3. Refuse blind repeated hyperparameter sweeps that violate the diversity rules.
4. Include correctness and overfit risks.
