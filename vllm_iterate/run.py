#!/usr/bin/env python3
"""Baseline embedding inference for vdr-multilingual-test.

Mirrors the processing in embedding_vllm.ipynb (Qwen3-VL-Embedding-2B via vLLM
with format_input_to_conversation / prepare_vllm_inputs). Every dataset row is
turned into one combined (query text + page image) input. All resulting
embeddings are saved to baseline_output.npy in row order matching the dataset
iteration order (sorted by language directory, then row index in parquet).
"""

import os
import io
import glob
import json
import time
import numpy as np
import pandas as pd
from typing import List, Dict, Any
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

from vllm import LLM
from vllm.multimodal.utils import fetch_image
from PIL import Image


BASE_DIR = "/dev/shm/vllm/vllm_baseline"
MODEL_PATH = os.path.join(BASE_DIR, "Qwen3-VL-Embedding-2B")
DATASET_DIR = os.path.join(BASE_DIR, "vdr-multilingual-test")
OUTPUT_PATH = "/dev/shm/auto_explore/vllm_iterate/result.npy"
METADATA_PATH = "/dev/shm/auto_explore/vllm_iterate/result_metadata.json"
INSTRUCTION = "Retrieve images or text relevant to the user's query."
SAMPLE_SIZE = 100
SAMPLE_SEED = 42


def format_input_to_conversation(
    input_dict: Dict[str, Any],
    default_instruction: str = "Represent the user's input.",
) -> List[Dict]:
    content = []

    instruction = input_dict.get("instruction") or default_instruction
    text = input_dict.get("text")
    image = input_dict.get("image")

    if image:
        image_content = None
        if isinstance(image, str):
            if image.startswith(("http://", "https://")):
                image_content = image
            else:
                abs_image_path = os.path.abspath(image)
                image_content = "file://" + abs_image_path
        else:
            image_content = image

        if image_content:
            content.append({"type": "image", "image": image_content})

    if text:
        content.append({"type": "text", "text": text})

    if not content:
        content.append({"type": "text", "text": ""})

    conversation = [
        {"role": "system", "content": [{"type": "text", "text": instruction}]},
        {"role": "user", "content": content},
    ]

    return conversation


def prepare_vllm_inputs(input_dict: Dict[str, Any], llm) -> Dict[str, Any]:
    conversation = format_input_to_conversation(input_dict)

    prompt_text = llm.llm_engine.tokenizer.apply_chat_template(
        conversation,
        tokenize=False,
        add_generation_prompt=True,
    )

    multi_modal_data = None
    image = input_dict.get("image")
    if image:
        if isinstance(image, str):
            if image.startswith(("http://", "https://")):
                try:
                    image_obj = fetch_image(image)
                    multi_modal_data = {"image": image_obj}
                except Exception as e:
                    print(f"Warning: Failed to fetch image {image}: {e}")
            else:
                abs_image_path = os.path.abspath(image)
                if os.path.exists(abs_image_path):
                    image_obj = Image.open(abs_image_path)
                    multi_modal_data = {"image": image_obj}
                else:
                    print(f"Warning: Image file not found: {abs_image_path}")
        else:
            multi_modal_data = {"image": image}

    return {"prompt": prompt_text, "multi_modal_data": multi_modal_data}


def decode_image(image_field: Any) -> Image.Image:
    if isinstance(image_field, Image.Image):
        return image_field
    if isinstance(image_field, dict) and image_field.get("bytes"):
        return Image.open(io.BytesIO(image_field["bytes"]))
    if isinstance(image_field, (bytes, bytearray)):
        return Image.open(io.BytesIO(image_field))
    raise ValueError(f"Unsupported image field type: {type(image_field)}")


def read_dataset(dataset_path: str):
    rows = []
    lang_stats: Dict[str, int] = {}

    parquet_files = sorted(glob.glob(os.path.join(dataset_path, "*", "*.parquet")))
    print(f"Found {len(parquet_files)} parquet files")
    for parquet_file in parquet_files:
        print(f"  - {parquet_file}")

    for parquet_file in tqdm(parquet_files, desc="Reading parquet files"):
        lang = os.path.basename(os.path.dirname(parquet_file))
        df = pd.read_parquet(parquet_file)
        lang_stats[lang] = len(df)
        for _, row in df.iterrows():
            rows.append(
                {
                    "id": row.get("id"),
                    "query": row.get("query"),
                    "image": row.get("image"),
                    "language": lang,
                }
            )

    return rows, lang_stats


def build_inputs(dataset_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    inputs = []
    for row in tqdm(dataset_rows, desc="Decoding images"):
        pil_image = decode_image(row["image"])
        inputs.append(
            {
                "text": row.get("query") or "",
                "image": pil_image,
                "instruction": INSTRUCTION,
            }
        )
    return inputs


def sample_rows(rows: List[Dict[str, Any]], n: int, seed: int):
    """Reproducibly pick n rows. Returns (sampled_rows, sampled_indices)."""
    rng = np.random.default_rng(seed)
    if n >= len(rows):
        indices = np.arange(len(rows))
    else:
        indices = np.sort(rng.choice(len(rows), size=n, replace=False))
    sampled = [rows[i] for i in indices]
    return sampled, indices.tolist()


def main():
    print("=" * 70)
    print("Step 1: Reading Dataset")
    print("=" * 70)
    dataset_rows, lang_stats = read_dataset(DATASET_DIR)
    total = sum(lang_stats.values())
    for lang, count in sorted(lang_stats.items()):
        print(f"  {lang}: {count:,}")
    print(f"  Total: {total:,}")

    print("\n" + "=" * 70)
    print(f"Step 1b: Sampling {SAMPLE_SIZE} rows (seed={SAMPLE_SEED})")
    print("=" * 70)
    dataset_rows, sampled_indices = sample_rows(dataset_rows, SAMPLE_SIZE, SAMPLE_SEED)
    sampled_lang_stats: Dict[str, int] = {}
    for r in dataset_rows:
        sampled_lang_stats[r["language"]] = sampled_lang_stats.get(r["language"], 0) + 1
    for lang, count in sorted(sampled_lang_stats.items()):
        print(f"  {lang}: {count}")
    print(f"  Sampled: {len(dataset_rows)} (from {total:,})")

    print("\n" + "=" * 70)
    print("Step 2: Initializing vLLM Model")
    print("=" * 70)
    N_REPLICAS = 2
    llms = []
    for _r_idx in range(N_REPLICAS):
        try:
            # G4: mm processor cache off + skip mm profiling. 100 unique multimodal
            # inputs make the LRU pure overhead; skipping mm-profiling recovers GPU
            # mem and shortens init. Generic vLLM knobs documented in Qwen3-VL recipe.
            _g4_kwargs = dict(
                model=MODEL_PATH,
                runner="pooling",
                dtype="bfloat16",
                trust_remote_code=True,
                gpu_memory_utilization=0.45,
                mm_processor_cache_gb=0,
                skip_mm_profiling=True,
            )
            try:
                _llm = LLM(**_g4_kwargs)
                print(f"G4: replica {_r_idx} constructed with mm cache disabled + profiling skip.")
            except (TypeError, ValueError) as _g4_err:
                print(f"G4: extra kwargs rejected for replica {_r_idx} ({_g4_err}); falling back.")
                _llm = LLM(
                    model=MODEL_PATH,
                    runner="pooling",
                    dtype="bfloat16",
                    trust_remote_code=True,
                    gpu_memory_utilization=0.45,
                )
            llms.append(_llm)
        except Exception as _llm_init_err:
            if _r_idx == 0:
                # First replica must succeed; re-raise.
                raise
            print(
                f"Warning: failed to construct LLM replica {_r_idx} "
                f"(falling back to N={_r_idx}): {_llm_init_err}"
            )
            break
    N_REPLICAS = len(llms)
    print(f"Constructed {N_REPLICAS} LLM replica(s).")
    llm = llms[0]  # keep this binding so prepare_vllm_inputs(inp, llm) and the K6 warmup keep working byte-identically

    print("\n" + "=" * 70)
    print("Step 3: Preparing Inputs")
    print("=" * 70)
    inputs = build_inputs(dataset_rows)
    vllm_inputs = [prepare_vllm_inputs(inp, llm) for inp in inputs]
    print(f"Prepared {len(vllm_inputs):,} samples")
    if vllm_inputs:
        print("\nPreview of the first prompt:")
        print(vllm_inputs[0]["prompt"][:200] + "...")

    print("\n" + "=" * 70)
    print("Step 3b: Synthetic JIT warmup (untimed)")
    print("=" * 70)
    try:
        warmup_instruction = "Synthetic warmup."
        warmup_text_short = "warmup"
        warmup_text_medium = "the quick brown fox " * 8
        warmup_text_long = "lorem ipsum dolor sit amet " * 40
        warmup_text_lengths = [warmup_text_short, warmup_text_medium, warmup_text_long]

        warmup_specs = []
        # 3 text-only specs
        for _wt in warmup_text_lengths:
            warmup_specs.append(
                {
                    "text": _wt,
                    "image": None,
                    "instruction": warmup_instruction,
                }
            )
        # 6 text+image specs over 3 sizes x 2 text lengths
        warmup_image_sizes = [(224, 224), (448, 336), (672, 504)]
        warmup_image_text_lengths = [warmup_text_short, warmup_text_medium]
        _warmup_rng = np.random.RandomState(0)
        for _w_h, _w_w in warmup_image_sizes:
            for _wt in warmup_image_text_lengths:
                _noise = _warmup_rng.randint(0, 256, size=(_w_h, _w_w, 3), dtype=np.uint8)
                _img = Image.fromarray(_noise)
                warmup_specs.append(
                    {
                        "text": _wt,
                        "image": _img,
                        "instruction": warmup_instruction,
                    }
                )

        warmup_vllm_inputs = [prepare_vllm_inputs(s, llm) for s in warmup_specs]
        print(f"Running synthetic warmup on {len(warmup_vllm_inputs)} specs...")
        _ = llm.embed(warmup_vllm_inputs)
        print("Synthetic warmup complete.")
    except Exception as _warmup_err:
        print(f"Warning: synthetic JIT warmup skipped due to: {_warmup_err}")

    # K1: also warm each additional replica's JIT cache to be safe.
    for _r_idx, _replica in enumerate(llms):
        if _replica is llm:
            continue
        try:
            _ = _replica.embed(warmup_vllm_inputs)
            print(f"Per-replica warmup complete for replica {_r_idx}.")
        except Exception as _replica_warmup_err:
            print(
                f"Warning: per-replica warmup skipped for replica {_r_idx} "
                f"due to: {_replica_warmup_err}"
            )

    print("\n" + "=" * 70)
    print("Step 4: Generating Embeddings")
    print("=" * 70)
    shards = [vllm_inputs[i::N_REPLICAS] for i in range(N_REPLICAS)]  # position-only
    embed_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=N_REPLICAS) as _pool:
        shard_outputs = list(_pool.map(lambda pair: pair[0].embed(pair[1]),
                                       list(zip(llms, shards))))
    embed_elapsed = time.perf_counter() - embed_start
    outputs = [None] * len(vllm_inputs)
    for r in range(N_REPLICAS):
        for k, o in enumerate(shard_outputs[r]):
            outputs[r + k * N_REPLICAS] = o
    assert all(o is not None for o in outputs), "stitch produced None"
    print(f"llm.embed() elapsed: {embed_elapsed:.4f} s "
          f"({embed_elapsed * 1000 / max(len(vllm_inputs), 1):.2f} ms/sample over "
          f"{len(vllm_inputs)} samples) ")
    print("inference samples per second: {:.4f}".format(len(vllm_inputs) / embed_elapsed if embed_elapsed > 0 else 0))

    embeddings = np.array([o.outputs.embedding for o in outputs])
    print(f"Embeddings shape: {embeddings.shape}")

    print("\n" + "=" * 70)
    print("Step 5: Saving Results")
    print("=" * 70)
    np.save(OUTPUT_PATH, embeddings)
    print(f"Saved embeddings to {OUTPUT_PATH} "
          f"({os.path.getsize(OUTPUT_PATH) / 1024 / 1024:.1f} MB)")

    metadata = {
        "total_samples": int(len(embeddings)),
        "embedding_dim": int(embeddings.shape[1]) if len(embeddings) else 0,
        "full_dataset_size": int(total),
        "full_language_distribution": lang_stats,
        "sampled_language_distribution": sampled_lang_stats,
        "sample_size": SAMPLE_SIZE,
        "sample_seed": SAMPLE_SEED,
        "sampled_indices_in_full_dataset": sampled_indices,
        "row_order": "sorted by language dir name, then parquet row index, then sampled by seed",
        "input_composition": "query text + page image per row (combined)",
        "instruction": INSTRUCTION,
        "model": MODEL_PATH,
        "embed_elapsed_seconds": embed_elapsed,
        "embed_per_sample_ms": embed_elapsed * 1000 / max(len(vllm_inputs), 1),
        "ids": [r["id"] for r in dataset_rows],
        "languages": [r["language"] for r in dataset_rows],
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to {METADATA_PATH}")


if __name__ == "__main__":
    main()