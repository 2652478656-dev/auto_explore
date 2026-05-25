# experiment-design skill

Use this skill whenever choosing or writing the next experiment.

The purpose is to keep the search mechanism-driven and diverse. A valid experiment is
not merely a parameter value; it is a falsifiable hypothesis about where time is being
spent.

## Hypothesis format

Write this before editing:

```md
## Hypothesis

- Family:
- Mechanism:
- Change:
- Why this should reduce x:
- Why y should remain > 0.999:
- Main correctness risk:
- Main overfit risk:
- Complexity cost:
- Minimal edit:
- Rollback condition:
- Follow-up if keep:
- Follow-up if fail:
```

## Family discipline

Families can evolve, but every run needs one primary family.

Examples:

- batching/scheduler
- prefix/cache reuse
- preprocess overlap
- async/parallelism
- precision/numerics
- memory/copy reduction
- output extraction
- runner path
- cleanup/removal
- combination
- instrumentation/profiling
- replica-concurrency
- process-thread-concurrency
- cuda-streams
- pipeline-overlap

## Anti-collapse gates

- Fourth consecutive same-family run is forbidden.
- Third consecutive scalar sweep of one knob is forbidden.
- Fourth consecutive known-local idea without a scout refresh is forbidden.
- A scout refresh that does not use external search counts as incomplete unless network
  access is unavailable or the orchestrator explicitly forbids it.
- A scout refresh that contains no local systems/radical ideas also counts as
  incomplete; external search is additive, not a replacement for local engineering
  exploration.
- Seventh completed experiment without external refresh is forbidden.
- If fewer than 30% of viable queued ideas are fresh, refresh before selecting another
  known direction.
- If fewer than 2 unexplored families are queued, refresh before selecting another
  known direction.
- A sweep is allowed only after a mechanism-bearing result.
- Five non-keeps triggers a forced portfolio refresh.
- A keep should be challenged by a different family before deep refinement.

## Novelty score

Score each candidate from 0 to 3:

- `0`: same knob, same mechanism, tiny mutation
- `1`: same family, new mechanism detail
- `2`: different family or materially different mechanism
- `3`: new family or cross-cutting insight

Prefer novelty `2` or `3` after repeated failures.
