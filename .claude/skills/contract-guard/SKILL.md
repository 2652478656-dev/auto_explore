# contract-guard skill

Use this skill before every run and before every keep.

## Baseline contract

`/dev/shm/auto_explore/vllm_iterate/run.py` must be identical to
`/dev/shm/vllm/vllm_baseline/run_baseline.py` except:

- embedding-call timed region
- output path to `/dev/shm/auto_explore/vllm_iterate/result.npy`

## Checks

Run:

```sh
diff -u /dev/shm/vllm/vllm_baseline/run_baseline.py /dev/shm/auto_explore/vllm_iterate/run.py
```

Inspect every hunk.

Allowed:

- code replacing `outputs = llm.embed(vllm_inputs)` and related timer bookkeeping
- helper code inside that replacement region if it does not alter fixed preprocessing
- output path change

Suspicious:

- new imports outside the allowed region
- changed constants
- changed sampling
- changed instruction text
- changed conversation formatting
- changed image loading or decoding
- changed input order
- changed metadata
- changed save logic beyond output path

If suspicious differences exist, block the run.
