# arxiv-mining skill

Use this skill to mine arXiv for inference optimization ideas.

The goal is not to summarize papers. The goal is to extract mechanisms that might
become local experiments under the current contract.

## Query families

Use combinations of:

- embedding inference optimization
- LLM inference batching
- prefix caching inference
- KV cache reuse
- multimodal inference optimization
- vision language model inference optimization
- continuous batching embedding models
- vLLM embedding performance
- GPU utilization small batch inference
- pooling model inference optimization
- CUDA graph LLM inference

## Extraction format

For every relevant paper:

```md
## Paper Idea

- Paper:
- Link:
- Year:
- Core mechanism:
- Workload studied:
- Requires training: yes/no
- Requires custom kernel: yes/no
- Requires new package: yes/no
- Applies to embedding inference: yes/no/maybe
- Fits current contract: yes/no/maybe
- Minimal local experiment:
- Main reason it may fail here:
```

## Rejection rules

Reject or mark `maybe` if the paper mainly depends on:

- training/fine-tuning
- changing model weights
- custom kernels unavailable locally
- serving architecture absent from this script
- generation-only decoding optimizations with no embedding analogue
- benchmark-specific shortcuts

## Output batch

Return at least:

- 2 conservative paper-derived ideas if available
- 2 medium-risk paper-derived ideas if available
- 1 weird/high-upside idea if available

If the search is weak, say exactly why.
