# idea-synthesis skill

Use this skill after external candidates have been scouted, triaged, translated, and
audited.

The purpose is to merge external ideas into the local search queue without letting
external research become another form of collapse.

## Inputs

Use:

- literature-scout candidates
- paper-triager decisions
- translated experiments
- source-auditor rulings
- current `research_state.md`
- recent `results.tsv`

## Queue rules

Add only ideas that:

- survived triage
- have a local minimal experiment
- passed source audit or have clear required fixes
- obey diversity constraints

Tag each queued idea with:

- source type
- source id/link
- local family
- freshness: fresh, known-family-new-mechanism, or known-repeat
- novelty score
- risk tier: conservative, medium, weird
- required pre-run audits

## Conflict handling

If an external idea conflicts with local evidence:

- explain the conflict
- downgrade priority unless the mechanism explains why prior attempts failed
- propose a smaller discriminating experiment

If an idea needs unavailable dependencies:

- translate to a no-new-dependency approximation, or reject it

If an idea improves work outside the allowed timed/contract region:

- reject it or mark as out of scope

## Output

```md
## Synthesized Queue Update

- Added:
- Deferred:
- Rejected:
- Diversity impact:
- Fresh idea ratio:
- Unexplored family count:
- Recommended next experiment:
- Why this is not just another local sweep:
```
