#!/usr/bin/env python3
import json
from pathlib import Path


INPUT_DIR = Path("data/final_clean_v2")
OUTPUT_DIR = Path("data/model_ready")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DROP_COLUMNS = {
    "id",
    "split",
    "source",
    "augmented",
    "attachment_type",
    "subtype",
    "era_bucket",
}


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def save_jsonl(rows, path):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def clean_rows(rows):
    cleaned = []

    for row in rows:
        cleaned_row = {
            k: v
            for k, v in row.items()
            if k not in DROP_COLUMNS
        }
        cleaned.append(cleaned_row)

    return cleaned


def process_split(split):
    input_path = INPUT_DIR / f"{split}.jsonl"
    output_path = OUTPUT_DIR / f"{split}.jsonl"

    rows = load_jsonl(input_path)
    cleaned = clean_rows(rows)

    save_jsonl(cleaned, output_path)

    original_cols = len(rows[0]) if rows else 0
    cleaned_cols = len(cleaned[0]) if cleaned else 0

    print(
        f"{split}: "
        f"{len(rows)} rows | "
        f"{original_cols} cols -> {cleaned_cols} cols"
    )


def main():
    for split in ["train", "val", "test"]:
        process_split(split)

    print("\nModel-ready dataset written to data/model_ready/")


if __name__ == "__main__":
    main()