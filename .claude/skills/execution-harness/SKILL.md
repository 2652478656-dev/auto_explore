# execution-harness skill

Use this skill to run an experiment, extract metrics, and append results.

## Run command

```sh
/dev/shm/vllm/venv/bin/python /dev/shm/auto_explore/vllm_iterate/run.py > /dev/shm/auto_explore/vllm_iterate/run.log 2>&1
```

Timeout: 5 minutes.

If timeout occurs, kill the process and classify as `crash`.

## Extract throughput

```sh
grep "inference samples per second:" /dev/shm/auto_explore/vllm_iterate/run.log
```

If missing, inspect:

```sh
tail -n 80 /dev/shm/auto_explore/vllm_iterate/run.log
```

## Score y

```sh
/dev/shm/vllm/venv/bin/python /dev/shm/vllm/vllm_baseline/cosine_similarity.py \
  /dev/shm/auto_explore/vllm_iterate/result.npy \
  /dev/shm/vllm/vllm_baseline/baseline_output.npy >> /dev/shm/auto_explore/vllm_iterate/run.log
```

Then:

```sh
grep "mean =" /dev/shm/auto_explore/vllm_iterate/run.log
```

## results.tsv

Append:

```tsv
commit	sample/s	y_cosine	memory_gb	status	family	description
```

Use:

- `0.0000` sample/s for crash
- `0.000000` y for crash or missing result
- `0.0` memory if unavailable

Never commit `results.tsv` unless explicitly requested.
