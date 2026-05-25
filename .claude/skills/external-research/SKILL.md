# external-research skill

Use this skill when local search is stale or the orchestrator needs more idea sources.

This skill defines the external research workflow. It should produce mechanisms that
can be triaged, translated, audited, and added to the local experiment queue.

## Trigger conditions

Run external research when:

- 6 completed experiments have happened since the last external refresh
- 5 consecutive experiments produce no keep
- current best has not improved after 10 experiments
- hypothesis queue has fewer than 4 viable candidates
- hypothesis queue has fewer than 2 unexplored families
- fresh ideas are below 30% of viable queued ideas
- `search-strategist` marks the portfolio stale
- entering an unfamiliar optimization family

## Source plan

Use at least 4 source types per refresh:

- arXiv
- vLLM GitHub issues/PRs
- Transformers/Hugging Face docs or blogs
- Qwen/Qwen-VL resources
- PyTorch/CUDA inference notes
- credible engineering blogs

Prefer primary sources and recent sources. For technical claims, primary sources beat
secondhand summaries.

## Required web scouts

Each full external refresh should call:

- `arxiv-scout` for papers
- `github-scout` for issues, PRs, discussions, and release notes
- `docs-scout` for official docs and examples
- `blog-scout` for engineering blogs when the other sources do not provide enough
  diversity

Do not let `literature-scout` be the only web-searching agent. It should coordinate and
merge, while source-specific scouts search deeply.

## Information boundaries

External research should not use benchmark reference embeddings.

The literature scout may see:

- code summaries
- environment constraints
- recent family outcomes
- bottleneck hypotheses

The implementer should receive only the translated local hypothesis, not the full score
history unless debugging requires it.

## Required output

Produce:

```md
## External Research Batch

- Trigger:
- Source types searched:
- Search queries:
- Candidate count:
- New families introduced:
- Known directions avoided:
- Source-specific scouts called:
- Coverage gaps:
- Conservative candidate:
- Medium-risk candidate:
- Weird/high-upside candidate:
- Rejected source themes:
```

Then send candidates to triage.
