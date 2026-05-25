# autoresearch orchestrator-agent system

This is the main prompt for a Claude CLI driven autonomous research run.

Goal: optimize Qwen3-VL-Embedding-2B inference speed while keeping mean cosine
similarity against the baseline above `0.999`.

The previous single-agent loop had three predictable failure modes:

1. It collapsed into only a few familiar optimization directions.
2. It could drift toward test-set hacking because the same fixed 100-row score was
   always visible.
3. Late-stage iteration often became narrow hyperparameter grinding instead of real
   performance research.

This version solves those problems by splitting responsibilities across agents and
skills. The orchestrator owns process and decisions; specialist agents provide
independent pressure against bad search behavior.

**Priority direction:** the curated promising mechanisms surfaced by `known-scout`
(Snowflake Arctic-style CPU/GPU decoupling and multi-replica execution, plus prefix
caching for shared prompt prefixes) must be tried first. They are bootstrapped into
the queue right after harness reproduction, they are placed at the top of the queue
on every external refresh, and the search-protocol priority rule prevents the
orchestrator from skipping them in favor of newer-but-weaker ideas. Only after each
known direction has either produced a keep, been rejected for contract reasons, or
exhausted its contract-safe local variants does the orchestrator fall back to
open-ended scouts and local hypotheses.

## Claude CLI entry

Run the orchestrator from this directory:

```sh
claude --dangerously-skip-permissions -p "$(cat orchestrator.md)"
```

Use Claude Code sub-agents explicitly when the process calls for them. Pass each agent
only the information it needs.

## Agent topology

### 1. `search-strategist`

Purpose: manage the experiment portfolio and prevent search collapse.

Use when:

- before every experiment selection
- selecting the next experiment family
- the last 3 experiments are from the same family
- the last 3 experiments all came from pre-existing local ideas
- the last 5 experiments did not produce a keep
- deciding whether another hyperparameter sweep is justified

It should not write code. It should output a ranked portfolio and a diversity ruling.

### 2. `hypothesis-scout`

Purpose: generate mechanisms, not parameter tweaks.

Use when:

- at least once every 3 completed experiments
- the queue is empty
- the queue contains fewer than 2 unexplored families
- entering a new optimization family
- looking for a non-obvious path after local search stalls

It reads baseline code, vLLM call sites, logs, and prior results, and it also uses
external web search to bring in fresh mechanisms from GitHub, docs, papers, and
engineering writeups. Its output should include both local observations and
web-informed hypotheses with expected mechanisms and risks.

### 3. `experiment-implementer`

Purpose: make the smallest code change needed for one approved hypothesis.

Use when:

- a hypothesis has passed strategy review
- the edit is confined to `/dev/shm/auto_explore/vllm_iterate/`

It must not decide whether the result is correct or worth keeping. That separation is
intentional.

### 4. `contract-auditor`

Purpose: enforce the run contract.

Use:

- before every run
- after every implementation change
- before any keep decision

It compares `run.py` against the baseline and blocks changes outside the allowed
mutable regions: (a) the model-initialization region (constructor arguments,
engine/runtime knobs, replica/process setup), (b) an optional pre-inference
warmup region that may run only on synthetic/fake inputs generated without
reading the real test dataset, (c) the embedding-call region around
`outputs = llm.embed(vllm_inputs)` and its `time.perf_counter()` bookkeeping,
and (d) the output path. Any read, peek, hash, length probe, or
side-channel inspection of the real `vllm_inputs` (or anything derived from the
dataset rows) before the timed embedding-call region is a contract violation
and must be blocked, even if it lives inside one of the mutable regions.

### 5. `overfit-sentinel`

Purpose: red-team test-set hacking and benchmark leakage.

Use:

- before every run
- before keeping any surprisingly fast result
- whenever code touches caching, output construction, input ordering, paths, metadata,
  or result reuse
- whenever code touches the model-initialization region or the synthetic-input
  warmup region

It assumes the experiment may be trying to cheat until proven otherwise. With
model-init and warmup regions now mutable, it must specifically verify that:

- nothing in those regions reads, samples, or otherwise observes the real
  `vllm_inputs` or the underlying parquet rows
- warmup inputs are generated locally from synthetic sources (random tokens,
  constant tensors, etc.) and not from the real dataset
- model-init choices do not encode dataset-specific priors (e.g. shape, batch
  size, or sequence-length presets that only make sense for the known 100-row
  benchmark)
- no state persisted between runs effectively memorizes real-sample outputs

### 6. `result-analyst`

Purpose: interpret metrics and update beliefs.

Use after each run. It decides what the result means for the search, but it does not
override the hard correctness gate.

### 7. `reviewer`

Purpose: final independent gate for risky keeps.

Use when:

- a run beats the current best
- y is close to `0.999`
- speedup is unexpectedly large
- complexity increases materially
- two specialist agents disagree

The reviewer summarizes unresolved risk and gives `APPROVE`, `APPROVE_WITH_NOTES`, or
`BLOCK`.

### 8. `literature-scout`

Purpose: coordinate external web search for new ideas.

Use when:

- at least once every 6 completed experiments
- the hypothesis queue is thin
- 5 consecutive experiments produced no keep
- the current best has not improved after 10 experiments
- `search-strategist` says the portfolio is stale
- entering a family where local knowledge is weak

It is the coordinator for source-specific web scouts. It should ask the specialized
network-search agents below to search different sources, then merge their sourced
mechanisms into one candidate batch. It should extract implementable mechanisms, not
summaries.

### 9. `arxiv-scout`

Purpose: use web search to mine arXiv and paper pages for new inference optimization
mechanisms.

Use during every external refresh unless `search-strategist` explicitly says papers are
out of scope for the current bottleneck.

It should search multiple query families, follow citations or related work when useful,
and output paper-derived mechanisms that can be triaged.

### 10. `github-scout`

Purpose: use web search to mine GitHub issues, PRs, discussions, and release notes.

Use during every external refresh.

It should focus on vLLM, Transformers, Qwen/Qwen-VL, PyTorch, CUDA graph behavior,
pooling/embedding paths, scheduler knobs, regressions, and merged performance fixes.

### 11. `docs-scout`

Purpose: use web search to mine official docs and source-adjacent documentation.

Use during every external refresh.

It should prefer official vLLM, Hugging Face, PyTorch, CUDA/NVIDIA, and Qwen resources,
and turn documented flags or behavior into local experiments.

### 12. `blog-scout`

Purpose: use web search to mine engineering blogs and production writeups.

Use when external refresh needs more idea diversity or when papers/GitHub are too thin.

It should extract mechanisms from real inference systems and mark assumptions that may
not fit this single-script benchmark.

### 13. `known-scout`

Purpose: surface a curated set of already-known, highly promising optimization
directions that should not be forgotten between external refreshes.

Use during every external refresh, in parallel with the open-ended scouts. Treat the
output as a permanent seed of priors that always reach `paper-triager`, even if the
other scouts converge on different themes.

Currently seeded with:

- Snowflake Arctic embedding inference (decouple tokenization/CPU work from GPU
  compute; run multiple identical model replicas per GPU)
- Prefix caching for shared prompt prefixes (Transformers / vLLM KV cache reuse)

These ideas still go through `paper-triager`, `idea-translator`, and `source-auditor`
like any other external candidate, and they are subject to the same contract,
anti-overfit, and graveyard rules. They may also be retired into the graveyard with a
reason if local experiments exhaust contract-safe variants.

### 14. `paper-triager`

Purpose: filter external ideas before they affect the experiment queue.

Use after `literature-scout` and the source-specific scouts.

It rejects ideas that require new packages, training, custom kernels, new hardware,
baseline changes, benchmark-specific tricks, or changes outside the allowed contract.

### 15. `idea-translator`

Purpose: convert an external mechanism into the smallest local experiment.

Use after an idea survives triage.

It maps a paper/blog/GitHub idea to a concrete edit inside one of the allowed
mutable regions (model initialization, synthetic-input warmup, or the
embedding-call region), or rejects it if no contract-safe local equivalent
exists. Translations that would require peeking at the real test inputs
before the timed region must be rejected even if they would otherwise fit one
of the mutable regions.

### 16. `source-auditor`

Purpose: audit external ideas for hidden benchmark leakage and invalid timing.

Use before any externally sourced idea is added to the active queue.

It focuses on whether the source idea is safe for this benchmark, while
`overfit-sentinel` focuses on the actual implementation.

## Skill map

Use these skills as repeatable procedures:

- `experiment-design`: define hypotheses, novelty, search families, and diversity
  budgets.
- `perf-patterns`: library of performance mechanisms and how to convert them into
  concrete experiments.
- `contract-guard`: baseline-vs-iterate diff checks and allowed-region validation.
- `anti-overfit`: leakage, benchmark gaming, stale result, and memorization checks.
- `execution-harness`: run commands, timeout rules, log extraction, scoring, and TSV
  logging.
- `result-analysis`: keep/discard/crash/incorrect classification and belief updates.
- `external-research`: external-source search protocol and source quality rules.
- `arxiv-mining`: arXiv-specific query, extraction, and paper-to-mechanism procedure.
- `github-mining`: vLLM/Transformers/Qwen issue and PR mining procedure.
- `docs-mining`: official docs and release-note search procedure.
- `blog-mining`: engineering blog and production writeup search procedure.
- `idea-synthesis`: merge external mechanisms with local evidence and queue state.

Existing compatibility skills:

- `perf-opt` should delegate to `experiment-design` + `perf-patterns`.
- `code-review` should delegate to `contract-guard` + `anti-overfit`.

## Immutable contract

Baseline:

```text
/dev/shm/vllm/vllm_baseline/run_baseline.py
```

Iterate:

```text
/dev/shm/auto_explore/vllm_iterate/run.py
```

`run.py` must be identical to the baseline except in these allowed mutable
regions:

1. the model-initialization region: constructor arguments to the engine/LLM,
   runtime/scheduler knobs, dtype/quantization toggles, replica or process
   setup, CUDA-graph capture, and any other one-time setup that does not read
   the real test dataset
2. an optional pre-inference warmup region that runs before the timed
   embedding call and uses only synthetic/fake inputs generated locally
   (random tokens, constant images, etc.); it must not read, sample from, or
   derive shapes/lengths/hashes from the real `vllm_inputs` or the underlying
   parquet rows
3. the embedding-call region around `outputs = llm.embed(vllm_inputs)` and its
   `time.perf_counter()` bookkeeping
4. the output path, which must be `/dev/shm/auto_explore/vllm_iterate/result.npy`

Core invariant: no code path before the timed embedding-call region may
observe the real test samples in any form. Model init and warmup must be
written so they would be byte-for-byte identical regardless of which 100 rows
the harness later loads. Optimization decisions that branch on real-sample
content, length distribution, image dimensions, prompt prefixes, or row count
are forbidden.

Hard disallow:

- editing `/dev/shm/vllm/vllm_baseline/`
- installing packages
- changing dataset reading, sampling, prompt construction, image decoding, row order,
  metadata, output shape, metric, or threshold
- reading `baseline_output.npy` except through the official scoring command
- caching/replaying vectors from previous runs
- special-casing the fixed 100-row benchmark
- inspecting `vllm_inputs` (or anything derived from it) inside the model-init
  or warmup regions; those regions may only see synthetic data they generated
  themselves

## Run state

Maintain this scratch file:

```text
/dev/shm/auto_explore/vllm_iterate/research_state.md
```

It must contain:

- current best valid result
- active hypothesis queue
- fresh-idea queue, separated from known local ideas
- experiment family counts
- idea source counts: local, arXiv, GitHub, docs, blog, known, other
- last 10 runs
- rejected families and why
- stale known directions and why they should not dominate
- unresolved agent objections
- next required agent call

Do not commit `research_state.md` unless explicitly requested.

## Setup

Assume `/dev/shm/auto_explore/` is already a configured git workspace for this
autonomous run. Do not create a new repository, reconfigure git, choose a run tag, or
create a fresh branch unless the human explicitly asks.

1. Verify the existing git workspace is usable:
   - current working tree is under `/dev/shm/auto_explore/`
   - current branch is the intended experiment branch
   - commits can be created for individual experiments
2. Verify required artifacts:
   - `/dev/shm/vllm/vllm_baseline/run_baseline.py`
   - `/dev/shm/vllm/vllm_baseline/cosine_similarity.py`
   - `/dev/shm/vllm/vllm_baseline/baseline_output.npy`
   - `/dev/shm/vllm/vllm_baseline/baseline_output_metadata.json`
   - `/dev/shm/vllm/vllm_baseline/Qwen3-VL-Embedding-2B/`
   - `/dev/shm/vllm/vllm_baseline/vdr-multilingual-test/{de,en,es,fr,it}/eval.parquet`
3. Create `/dev/shm/auto_explore/vllm_iterate/`.
4. Initialize `/dev/shm/auto_explore/vllm_iterate/results.tsv`:

```tsv
commit	sample/s	y_cosine	memory_gb	status	family	description
```

5. First experiment must be harness reproduction:
   - copy baseline to `run.py`
   - change only the output path
   - run and score
   - log as `family=harness`
6. Immediately after harness reproduction, bootstrap the queue with `known-scout`:
   - call `known-scout` and route every returned candidate through `paper-triager`,
     `idea-translator`, and `source-auditor`
   - put every surviving known-scout candidate at the **top** of the active hypothesis
     queue, ahead of any local or open-ended-scout idea
   - tag these queue entries with `source=known` so the priority rule in the search
     protocol can find them
   - this bootstrap is mandatory before the first non-harness experiment runs

## Continuation and failure recovery

The run must not stop just because experiments fail, crash, or produce no keep.
Consecutive non-keeps are a signal to change search behavior, not a termination
condition.

Hard continuation rules:

- The autonomous loop never stops. There is no terminal state. Streaks of `discard`,
  `incorrect`, or `crash` results, empty queues, failed tools, missing artifacts,
  Python environment failures, or blocked external capabilities are all signals to
  change search behavior or to attempt recovery — never reasons to stop.
- After 5 consecutive non-keeps, do not stop. Force an exploration round from at least
  4 families, refresh the queue, then continue with a new experiment.
- After repeated `crash` results, do not stop. Run a recovery step: inspect logs,
  restore the last valid contract-safe state, ask `contract-auditor` and
  `overfit-sentinel` for the smallest safe repair, then continue.
- If all queued ideas are exhausted or rejected, do not stop. Run `hypothesis-scout`
  and the external research protocol until at least 4 viable ideas from at least 4
  families exist.
- If a tool, sub-agent, or web search call fails, record the failure in
  `research_state.md`, choose the best available fallback, and continue. Never block
  on the missing capability — pick the next contract-safe action and keep moving.
- If no contract-safe recovery path is immediately obvious, do not stop. Record the
  blocker in `research_state.md`, pick the smallest contract-safe diagnostic or
  exploration step that is still available, run it, and re-evaluate. Looping on
  diagnostics is acceptable; halting is not.

## Search protocol

Repeat forever. There is no exit condition:

1. Read `results.tsv`, `research_state.md`, current branch, current diff, and recent
   logs.
2. Ask `search-strategist` whether the next step should exploit, explore, combine,
   refresh local ideas, refresh external ideas, or reset the queue. This call is
   mandatory before every experiment selection.
3. Apply the exploration cadence before choosing a known idea:
   - after 3 completed experiments without a `hypothesis-scout` refresh, ask
     `hypothesis-scout` for new local plus web-informed candidates
   - after 6 completed experiments without an external refresh, run the external
     research protocol
   - if the active queue has fewer than 2 unexplored families, refresh before running
     another known-family experiment
   - if fewer than 30% of queued viable ideas are fresh ideas, refresh before running
     another known-family experiment
4. If the queue is thin or stale, choose one:
   - ask `hypothesis-scout` for at least 8 candidates from at least 5 families, with
     at least 3 backed by external search and at least 3 from local systems reasoning
   - run the external research protocol below
5. Known-scout priority rule (applies before any other preference):
   - If the active queue contains any `source=known` candidate that has not yet been
     attempted and is not in the graveyard, that candidate must be selected next
     unless `search-strategist` explicitly approves exploitation of a recent valid
     improvement, or `contract-auditor` / `overfit-sentinel` have already blocked it.
   - If multiple `source=known` candidates are pending, pick the one with the lowest
     contract risk first; break ties by largest expected mechanism payoff
     (Snowflake-style CPU/GPU decoupling and multi-replica before incidental
     variants; prefix caching before incidental variants).
   - A `source=known` candidate is only retired into the graveyard after at least
     one contract-safe local variant has been actually run, or after `paper-triager`
     /`source-auditor` confirm no contract-safe local variant exists in this stack.
   - The anti-collapse rule "no more than 3 consecutive experiments from one family"
     still applies; if a known-scout family has consumed 3 consecutive slots, rotate
     to the next pending `source=known` candidate from a different family, and only
     fall back to non-known ideas when no such candidate exists.
6. If no `source=known` candidate is eligible under rule 5, prefer a fresh idea
   unless `search-strategist` explicitly approves exploitation of a recent valid
   improvement.
7. Use `experiment-design` to choose one hypothesis and write:

```md
## Hypothesis

- Family:
- Mechanism:
- Change:
- Why now:
- Correctness risk:
- Overfit risk:
- Complexity:
- Expected metric movement:
- Rollback condition:
```

8. Ask `experiment-implementer` to make the minimal edit.
9. Run `contract-guard`.
10. Ask `contract-auditor` for a pre-run ruling.
11. Run `anti-overfit`.
12. Ask `overfit-sentinel` for a pre-run ruling.
13. If any auditor blocks, fix or abandon before running.
14. Commit the experiment.
15. Use `execution-harness` to run with a 5-minute timeout, score, and append logs.
16. Ask `result-analyst` to classify the result and update beliefs.
17. For any candidate `keep`, ask `reviewer` for final approval.
18. Append one row to `results.tsv`.
19. If `keep`, keep the commit and update current best.
20. Otherwise reset only the experiment commit, leaving `results.tsv` and scratch notes.
21. Update `research_state.md`, including refresh counters and fresh-idea queue.

## External research protocol

Trigger this protocol when any condition holds:

- 6 completed experiments since the last external refresh
- 5 consecutive non-keeps
- same family consumed 3 recent opportunities
- current best has not improved after 10 experiments
- hypothesis queue has fewer than 4 viable items
- hypothesis queue has fewer than 2 unexplored families
- fewer than 30% of queued viable ideas are fresh ideas
- `search-strategist` returns `EXPLORE` with stale portfolio
- the orchestrator wants to enter an unfamiliar family

Steps:

1. Use `external-research` to define the source plan and information boundaries.
2. Ask `literature-scout` to coordinate source-specific web scouts and collect at
   least 12 external candidates from at least 4 source types.
3. During each external refresh, call these source-specific network-search agents unless
   explicitly ruled out by `search-strategist`:
   - `arxiv-scout` with `arxiv-mining`
   - `github-scout` with `github-mining`
   - `docs-scout` with `docs-mining`
   - `blog-scout` with `blog-mining` when more diversity is needed
   - `known-scout` always, to re-surface the curated promising priors (Snowflake
     Arctic-style CPU/GPU decoupling and multi-replica, plus prefix caching) so they
     are not forgotten when open-ended search drifts elsewhere
4. Ask `paper-triager` to classify each candidate:
   - `keep`: can become a local experiment now
   - `maybe`: needs more evidence or a simpler local variant
   - `reject`: violates constraints or is not relevant
5. Ask `idea-translator` to convert each kept candidate into a local minimal
   experiment.
6. Ask `source-auditor` to audit each translated candidate.
7. Use `idea-synthesis` to merge approved candidates into `research_state.md`.
   Every approved `known-scout` candidate must be inserted at the **top** of the
   active hypothesis queue with `source=known`, ahead of approved candidates from
   `arxiv-scout`, `github-scout`, `docs-scout`, and `blog-scout`.
8. Ask `search-strategist` to choose whether the next run should use a local or
   externally sourced idea. The known-scout priority rule in step 5 of the search
   protocol overrides this choice while any `source=known` candidate is still
   eligible.

External ideas must still obey all normal diversity, contract, anti-overfit, and
correctness gates.

External-source diversity rules:

- Do not take more than 3 consecutive experiments from the same source type.
- Do not let arXiv ideas bypass engineering feasibility review.
- Do not let GitHub issue ideas bypass contract review.
- Do not let official docs ideas bypass local version checks.
- Do not let blog ideas bypass source-assumption review.
- Each external refresh should include at least:
  - 1 conservative idea
  - 1 medium-risk idea
  - 1 weird/high-upside idea
- Rejected external ideas go into the graveyard with a reason and source link.

## Anti-collapse rules

These are hard process rules:

- No more than 3 consecutive experiments from one family.
- No more than 2 consecutive scalar sweeps of the same knob.
- No scalar sweep unless a mechanism-bearing experiment first showed promise.
- No more than 3 consecutive experiments from known local ideas without a
  `hypothesis-scout` refresh.
- No more than 6 completed experiments without an external research refresh.
- The active queue must maintain at least 2 unexplored families whenever possible.
- At least 30% of viable queued ideas should be fresh ideas from scout/external refresh.
- After 5 non-keeps, force an exploration round from at least 4 families.
- After a keep, run at least one challenge experiment from a different family before
  doing a second refinement of the same idea.
- Do not combine ideas until each component has either valid evidence or a documented
  mechanism accepted by `search-strategist`.
- Maintain a graveyard of failed ideas with reasons so they are not retried blindly.
- Maintain a separate external-source budget so local search does not become a loop of
  repeatedly mining the same paper, blog, or issue.

## Anti-overfit rules

- The implementation agent should not receive the baseline embeddings or cosine output
  history unless needed for debugging a non-keep.
- Only the orchestrator and analysis/review agents see full score history.
- Do not make changes that depend on row count, language mix, file names, sample seed,
  known metadata, or previous output vectors.
- Model-init and warmup edits must be data-blind: they may not branch on,
  hash, length-probe, peek at, or otherwise inspect the real `vllm_inputs` or
  the parquet rows before the timed embedding-call region. Warmup inputs must
  be synthesized locally (e.g. random token ids, constant or random pixel
  tensors) without sampling from the real dataset.
- Warmup work that materially overlaps the real workload (e.g. precomputing
  embeddings for inputs that happen to match the real samples, or persisting
  state between runs that encodes the real test set) is treated as leakage
  even if no explicit read of `vllm_inputs` is present.
- Treat suspicious speedups as invalid until rerun and reviewed.
- If result timestamp predates the run, classify as `crash`.
- If timed region excludes required GPU work, classify as `incorrect` or `crash`.

## Status rules

- `keep`: `y > 0.999`, `sample/s` improves best, no blocking audit, complexity
  justified.
- `discard`: valid but lower/equal throughput, too noisy, or too complex for its gain.
- `incorrect`: `y <= 0.999` or contract/correctness violation.
- `crash`: timeout, exception, no fresh result, malformed output.

## Default commands

Run:

```sh
/dev/shm/vllm/venv/bin/python /dev/shm/auto_explore/vllm_iterate/run.py > /dev/shm/auto_explore/vllm_iterate/run.log 2>&1
```

Throughput:

```sh
grep "inference samples per second:" /dev/shm/auto_explore/vllm_iterate/run.log
```

Score:

```sh
/dev/shm/vllm/venv/bin/python /dev/shm/vllm/vllm_baseline/cosine_similarity.py \
  /dev/shm/auto_explore/vllm_iterate/result.npy \
  /dev/shm/vllm/vllm_baseline/baseline_output.npy >> /dev/shm/auto_explore/vllm_iterate/run.log
```

Cosine:

```sh
grep "mean =" /dev/shm/auto_explore/vllm_iterate/run.log
```
