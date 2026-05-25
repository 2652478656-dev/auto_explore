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
    llm = LLM(
        model=MODEL_PATH,
        runner="pooling",
        dtype="bfloat16",
        trust_remote_code=True,
    )

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
    print("Step 4: Generating Embeddings")
    print("=" * 70)
    embed_start = time.perf_counter()
    outputs = llm.embed(vllm_inputs)
    embed_elapsed = time.perf_counter() - embed_start
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