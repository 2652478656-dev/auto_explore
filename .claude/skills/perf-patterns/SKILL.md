# perf-patterns skill

Use this skill when generating concrete performance ideas.

## Mechanism library

Look for ways to reduce:

- repeated prefix work
- GPU idle time
- small-batch inefficiency
- Python overhead inside the timed region
- CPU/GPU synchronization
- tensor copies and conversions
- allocation churn
- output object construction overhead
- unnecessary precision
- serialized preprocessing or postprocessing
- underused GPU caused by one serialized embedding call
- host-side scheduling gaps between independent inputs

## Candidate patterns

- vLLM scheduler knobs: `max_num_seqs`, `max_num_batched_tokens`, chunked prefill.
- Prefix/cache reuse: enable vLLM prefix caching or warm shared prompt paths.
- Batching: group inputs to improve occupancy without changing order.
- Async overlap: prepare next batch while current batch runs.
- Replica concurrency (high priority — propose concretely, not vaguely):
  - **In-process multi-`LLM`**: build N `LLM(...)` instances in the model-init
    region with reduced `gpu_memory_utilization` per replica; shard
    `vllm_inputs` and dispatch concurrently with `ThreadPoolExecutor` or
    `asyncio.gather` in the timed region; concatenate in original row order.
  - **Process-pool replicas**: spawn N workers via `multiprocessing.spawn` or
    `ProcessPoolExecutor` (use `set_start_method("spawn")`), one `LLM` per
    worker, all sharing the GPU. Shard `vllm_inputs` at embed time, gather
    in order.
  - **`AsyncLLMEngine`**: replace synchronous `LLM` with one or more async
    engines in init; submit all requests via `asyncio.gather` in the timed
    region. Often the simplest path to replica-style concurrency.
  - **`data_parallel_size`** vLLM constructor argument when the installed
    version supports it for pooling/embedding runners.
- Process/thread parallelism: use worker processes or threads only when model/runtime
  behavior supports real overlap and does not hide required timed work. Spawn
  the workers in the model-init region, not at embed time.
- CUDA streams/async dispatch: overlap independent GPU work where the backend
  permits it. Single-engine variant of replica concurrency — dedicate streams
  for H2D copy, encoder forward, and pooling, created in init.
- Microbatch pipeline: split inputs into staged chunks to overlap launch, execution, and
  output extraction.
- Output extraction: avoid repeated Python conversions where possible.
- Precision: use lower precision only when cosine remains safely above threshold.
- Cleanup: remove redundant synchronization or object copying.
- Combination: merge two independently valid improvements.

## Proposal rule

Every proposal must name:

- the bottleneck it targets
- why it is plausible in this codebase
- how it could fail
- the smallest first experiment

Do not propose benchmark-specific shortcuts.
