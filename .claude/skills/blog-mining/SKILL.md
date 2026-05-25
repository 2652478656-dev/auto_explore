# blog-mining skill

Use this skill with `blog-scout` to mine engineering blogs and production writeups.

## Extraction

For each useful writeup:

```md
## Blog Idea

- Source:
- Link:
- Production context:
- Mechanism:
- Local approximation:
- Assumptions:
- Contract risk:
- Transfer risk:
```

## Rules

- Prefer blogs with concrete measurements or implementation details.
- Mark ideas requiring request batching, serving queues, distributed systems, or custom
  kernels as high transfer risk.
- Convert broad architecture ideas into the smallest local experiment.
- Reject ideas that depend on benchmark-specific shortcuts or reference outputs.
