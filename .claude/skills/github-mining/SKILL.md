# github-mining skill

Use this skill to mine engineering sources, especially GitHub issues and PRs.

Target repositories and docs:

- vLLM
- Transformers
- Qwen/Qwen2.5-VL/Qwen3-VL model resources
- PyTorch inference notes

## Search targets

Look for:

- `LLM.embed`
- pooling models
- prefix caching
- chunked prefill
- CUDA graph
- scheduler config
- `max_num_seqs`
- `max_num_batched_tokens`
- multimodal processor performance
- async output processing
- memory allocation regressions
- embedding throughput

## Extraction format

```md
## Engineering Idea

- Source:
- Link:
- Component:
- Reported behavior:
- Mechanism:
- Version relevance:
- Local first experiment:
- Contract risk:
- Dependency risk:
- Why it may not apply:
```

## Rules

- Prefer issues/PRs with maintainer comments, merged fixes, benchmarks, or clear
  reproduction details.
- Treat unmerged issue comments as weak evidence.
- Check version relevance against the local environment when possible.
- Do not propose package upgrades unless explicitly allowed.
- Convert config discoveries into minimal experiments.
