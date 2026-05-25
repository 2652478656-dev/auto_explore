# auto_explore results summary

Autonomous research run optimizing `Qwen3-VL-Embedding-2B` inference throughput
on the 100-row vdr-multilingual-test benchmark, with `y_cosine > 0.999` as the
hard correctness gate. Full log: [vllm_iterate/results.tsv](vllm_iterate/results.tsv).

## Headline numbers

- **Baseline**: 4.2501 sample/s (harness reproduction, `f53ccd8`)
- **Current best**: **10.2972 sample/s** (`2d7dd23`, mm-cache G4) — **2.42x** vs baseline
- **Correctness**: every kept run holds `y_cosine = 1.000000`
- **Runs so far**: 7 (4 keep, 1 discard, 2 crash)

## Experiment timeline

| # | commit  | family        | status   | sample/s | vs baseline | mechanism                                                                  |
|---|---------|---------------|----------|----------|-------------|----------------------------------------------------------------------------|
| 1 | f53ccd8 | harness       | keep     | 4.2501   | 1.00x       | baseline copy with output path redirected                                  |
| 2 | ce80207 | warmup        | keep     | 6.4725   | 1.52x       | K6 synthetic JIT warmup (untimed); eliminates JIT events in timed pass     |
| 3 | f0b3546 | multi-replica | crash    | —        | —           | K1 first attempt; `gpu_memory_utilization=0.40` → KV cache OOM             |
| 4 | a4467c7 | multi-replica | **keep** | 9.8513   | **2.32x**   | K1 N=2 in-process replicas + `ThreadPoolExecutor`; `gmu=0.45` each         |
| 5 | 4208fe3 | multi-replica | crash    | —        | —           | K5 N=2 `spawn` workers; vLLM memory-profile assertion under concurrent init |
| 6 | 593b6c4 | cudagraph     | discard  | 9.9712   | 2.35x       | Stack A capture-ladder pin; +1.2% over K1 — within noise, not worth complexity |
| 7 | 2d7dd23 | mm-cache      | **keep** | 10.2972  | **2.42x**   | G4 `mm_processor_cache_gb=0` + `skip_mm_profiling=True`; stacks on K1+K6   |

## What's working

The current best stacks three independent wins:

1. **Synthetic warmup (K6)** — pre-trigger Triton JIT (`_compute_slot_mapping_kernel`,
   `_bilinear_pos_embed_kernel`, `rotary_kernel`) outside the timed region so the
   first real batch doesn't pay compile cost. +52% over baseline.
2. **Multi-replica in-process (K1)** — two `LLM(...)` instances on one GPU at
   `gpu_memory_utilization=0.45` each, dispatched via `ThreadPoolExecutor`
   inside the embed region. +53% on top of warmup. Snowflake Arctic direction.
3. **Multimodal cache off (G4)** — `mm_processor_cache_gb=0` plus
   `skip_mm_profiling=True`. With 100 unique images the mm cache is dead weight;
   skipping profiling recovers GPU memory headroom. +4.5% on top of K1.

## What didn't work (graveyard highlights)

- **K2 / K8** (pre-tokenization, CPU/GPU pipeline): would require reading real
  `vllm_inputs` before the timed region → contract violation (peeks at test samples).
- **K3** (prefix-cache priming): moves required embed work outside the timer.
- **K4** (AsyncLLMEngine): vLLM 0.21.0 V1 pooling runner has no stable
  `AsyncLLMEngine.encode`; fallback collapses to K1.
- **K5** (multi-process replicas via `spawn`): vLLM V1 engine asserts
  `init_snapshot.free_memory >= free_gpu_memory` under concurrent process init.
  Empirically subsumed by K1 threads at this scale.
- **K7** (user-level CUDA streams): vLLM owns H2D scheduling; user streams
  around synchronous `llm.embed` cannot overlap anything.
- **Stack A capture-ladder pin**: numerically positive but inside noise band.

## Live research state

The active hypothesis queue, refresh counters, idea-source budget, and pending
agent calls live in
[vllm_iterate/research_state.md](vllm_iterate/research_state.md).
The orchestrator agent topology and contract are in
[orchestrator.md](orchestrator.md).


## Logs

All the logs are under [logs](logs) folder