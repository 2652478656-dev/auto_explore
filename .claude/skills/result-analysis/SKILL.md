# result-analysis skill

Use this skill after every experiment.

## Classification

`keep` requires:

- `y > 0.999`
- `sample/s` improves the current best
- contract audit passed
- anti-overfit audit passed
- complexity is justified

`discard`:

- y passes, but `sample/s` is equal/lower
- speedup is too small for complexity
- result is too noisy and rerun does not confirm it

`incorrect`:

- `y <= 0.999`
- contract drift
- benchmark leakage
- timer excludes required work

`crash`:

- timeout
- exception
- missing result
- stale result
- malformed output

## Belief update

For each run, write:

- what mechanism was supported or refuted
- whether the family deserves another attempt
- whether the next attempt should explore, exploit, combine, or abandon
- what evidence would change the decision

Do not let an incorrect fast run become the main guide for future tuning.
