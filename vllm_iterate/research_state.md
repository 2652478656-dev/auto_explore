# research_state

Scratch file for the autonomous research run. Updated after every experiment.

## current best valid result

- commit: `a4467c7`
- family: `multi-replica`
- sample/s: **9.8513** (+131.8% vs harness, +52.2% vs K6)
- y_cosine: 1.000000
- memory_gb: 4.31 (per-replica)
- note: K1 N=2 in-process LLM replicas with ThreadPoolExecutor and `[i::N]` sharding, gmu=0.45 each. Stacks with K6 warmup. APPROVE_WITH_NOTES from reviewer (gmu margin thin; N>=3 likely OOM).

## active hypothesis queue (ordered)

1. **Stack A — capture-ladder pin** (`source=docs+github+arxiv`, family=cudagraph). One coherent experiment combining: P5 (extend K6 warmup with batch-size ladder), G2/D1 (pin `cudagraph_capture_sizes=[1,2,4,8,16,32,64]`), D2 (`cudagraph_num_of_warmups=2`), D7 (`max_num_seqs=64`). Documented mechanism: shrink default 51-bucket ladder to 7 buckets, ensure per-replica batch (~50) lands in the 64-bucket, pre-replay every graph during warmup. Source-auditor & idea-translator approved. Locked rationale: ladder=power-of-2, NOT derived from 100/2=50.
2. **G4 — multimodal cache off** (`source=github+docs`, family=cudagraph). Standalone: `mm_processor_cache_gb=0, skip_mm_profiling=True`. With 100 unique images cache is dead weight; profiling skip recovers GPU mem.
3. **Stack B — host-side micro-bundle** (`source=arxiv+docs`, family=host). P4 (hoist params, pin affinity) + P6 (`torch.set_float32_matmul_precision("high")`) + D4 (`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`). Lowest risk, smallest expected payoff, stacks with everything.
4. **P1/G3 — `cudagraph_mm_encoder: True`** (`source=arxiv+github`, family=cudagraph). Documented +11-19% Qwen3-VL-specific. MAYBE: confirm flag exists in 0.21.0 first.

After Stack A: rotate family to non-cudagraph (per anti-collapse) for next experiment, then return.

## fresh-idea queue (separated from known local ideas)

(empty pending external research — first refresh due after 6 non-harness experiments)

## experiment family counts

| family | runs |
|---|---|
| harness | 1 |
| warmup | 1 (keep) |
| multi-replica | 3 (2 crash, 1 keep) |

## idea source counts

| source | count |
|---|---|
| local | 0 |
| arXiv | 6 surfaced (P1-P6); 1 kept (P5 in Stack A), 1 maybe (P1), 1 reject (P2) |
| GitHub | 7 surfaced (G1-G7); 2 kept (G2/G4), 1 maybe (G3) |
| docs | 8 surfaced (D1-D8); 5 kept (D1/D2/D4/D7); 1 reject (D6) |
| blog | 0 (skipped in refresh #1 — 3 sources already gave 21 candidates) |
| known | 3 used (K6, K1 keep; K5 graveyard); K3,K4,K2,K7,K8 graveyard |
| other | 0 |

## last 10 runs

| # | commit | family | status | sample/s | y_cosine |
|---|---|---|---|---|---|
| 1 | f53ccd8 | harness | keep | 4.2501 | 1.000000 |
| 2 | ce80207 | warmup | keep | 6.4725 | 1.000000 |
| 3 | f0b3546 | multi-replica | crash | n/a | n/a (KV cache OOM at gmu=0.40) |
| 4 | a4467c7 | multi-replica | keep | 9.8513 | 1.000000 |
| 5 | 4208fe3 | multi-replica | crash | n/a | n/a (concurrent spawn init asserts in vLLM memory profiler; reset) |

## rejected families and why

(none yet)

## graveyard (rejected ideas with reason)

- **K2** (CPU/GPU pipeline, pre-tokenization) — REJECTED by paper-triager. Tokenization/PIL decode must happen on real `vllm_inputs`; moving it before the timer is a contract violation (peeks at real samples). Keeping it inside the timer overlaps nothing vLLM is not already overlapping.
- **K3** (prefix-cache priming with shared INSTRUCTION prefix) — BLOCKED by source-auditor. Although the prefix is a script constant, priming the shared-prefix KV outside the timer relocates required embed work out of the measured window. Auto prefix-caching would already amortize within the timed batch.
- **K4** (AsyncLLMEngine async submission) — REJECTED by idea-translator. vLLM 0.21.0 V1 pooling-runner does not expose a stable AsyncLLMEngine.encode for `runner="pooling"`. The fallback (concurrent.futures over `llm.embed`) collapses to K1.
- **K7** (user-level CUDA streams) — REJECTED by paper-triager. vLLM owns H2D scheduling; user-level streams around the synchronous `llm.embed` cannot overlap anything.
- **K8** (pre-tokenization via `prompt_token_ids`) — REJECTED by paper-triager. Requires tokenizing real prompts before the timed region — contract violation (peeks at real samples).
- **K5** (multi-replica spawn, multi-process) — STRUCTURAL BLOCKER, graveyard. vLLM 0.21.0 V1 engine asserts `init_snapshot.free_memory >= free_gpu_memory` when two LLMs init concurrently in spawned processes (memory profiler intolerant of allocation churn from sibling process). One worker also hit the same KV-cache-OOM as K1's first attempt at gmu=0.40. Sequential init would also be slower than K1 threads on a 100-sample workload, so K5's mechanism is empirically subsumed by K1.

## stale known directions and why they should not dominate

(none yet — known-scout seeds are still pending bootstrap)

## unresolved agent objections

(none)

## refresh counters

- experiments since last `hypothesis-scout` refresh: 4 (K6, K1-crash, K1, K5-crash) — TRIGGER NOW
- experiments since last external refresh: 4 — trigger now (last known-scout consumed)
- consecutive non-keeps: 1 (K5 crash)
- consecutive same-family runs: 3 (multi-replica — graveyard or rotate)
- Trigger external research protocol now: known-scout exhausted, queue is empty, last K5 was a crash.

## interesting log signals from the harness run

The vLLM run.log shows triton kernels JIT-compiled DURING inference (latency spike):
`_compute_slot_mapping_kernel`, `_bilinear_pos_embed_kernel`, `rotary_kernel`. These
are contract-safe warmup-region opportunities once known-scout candidates are tried.

Engine config notes (potentially mutable in model-init region):
- enforce_eager=False, cudagraph_mode=PIECEWISE, capture sizes 1..512
- enable_prefix_caching=True, enable_chunked_prefill=True
- gpu_memory_utilization=0.92 (effective ~0.9155 with cudagraph profiling)
- Model loading took 4.31 GiB; Available KV cache 66.71 GiB (large headroom)

## next required agent call

External research protocol: `literature-scout` to coordinate `arxiv-scout`, `github-scout`, `docs-scout`, `blog-scout`, `known-scout` in parallel. Then `paper-triager`, `idea-translator`, `source-auditor`, `idea-synthesis`. Emphasis (from search-strategist): V1-engine pooling flags, CUDA graphs deeper + enforce_eager, flashinfer/flashattn backend, compile mode, pooled-output extraction overhead, dtype, attention impl.
