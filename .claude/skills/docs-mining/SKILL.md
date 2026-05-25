# docs-mining skill

Use this skill with `docs-scout` to mine official documentation and release notes.

## Sources

Prefer:

- vLLM official docs
- Hugging Face Transformers docs
- PyTorch docs
- NVIDIA/CUDA docs
- Qwen official model cards and examples

## Extraction

For each useful documented feature:

```md
## Docs Idea

- Source:
- Link:
- Feature:
- Local version requirement:
- Mechanism:
- Minimal local experiment:
- Contract risk:
- Why it may not apply:
```

## Rules

- Do not propose package upgrades unless explicitly allowed.
- Check whether the documented feature exists in the local installed version.
- Reject docs ideas that require serving infrastructure absent from the script.
- Prefer documented knobs that can be tested inside the embedding-call region.
