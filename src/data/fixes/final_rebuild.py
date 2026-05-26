#!/usr/bin/env python3
import json
import hashlib
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


INPUT_FILES = [
    "data/processed/train.jsonl",
    "data/processed/val.jsonl",
    "data/processed/test.jsonl",
]

OUT_DIR = Path("data/final_clean_v2")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15
RANDOM_STATE = 42


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def save_jsonl(df, path):
    with open(path, "w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")


def normalize_text(text):
    if pd.isna(text):
        return ""
    return " ".join(str(text).lower().split())


def hash_body(text):
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def main():
    print("Loading raw datasets...")

    dfs = [load_jsonl(path) for path in INPUT_FILES]
    df = pd.concat(dfs, ignore_index=True)

    print(f"Raw total: {len(df)}")

    # Separate augmented rows
    augmented_df = df[df["augmented"] == True].copy()
    real_df = df[df["augmented"] == False].copy()

    print(f"Real samples: {len(real_df)}")
    print(f"Augmented samples: {len(augmented_df)}")

    # Global deduplication on body text
    real_df["body_hash"] = real_df["body_text"].apply(hash_body)

    before = len(real_df)
    real_df = real_df.drop_duplicates(subset=["body_hash"]).copy()
    after = len(real_df)

    print(f"Removed duplicate real emails: {before - after}")

    # Stratify by label + source
    real_df["stratify_key"] = (
        real_df["label"].astype(str) + "__" + real_df["source"].astype(str)
    )

    counts = real_df["stratify_key"].value_counts()
    valid_keys = counts[counts >= 3].index

    dropped = real_df[~real_df["stratify_key"].isin(valid_keys)]
    real_df = real_df[real_df["stratify_key"].isin(valid_keys)].copy()

    print(f"Dropped rare strata rows: {len(dropped)}")

    # Split real data
    train_real, temp = train_test_split(
        real_df,
        test_size=(1 - TRAIN_RATIO),
        stratify=real_df["stratify_key"],
        random_state=RANDOM_STATE,
    )

    val_real, test_real = train_test_split(
        temp,
        test_size=0.5,
        stratify=temp["stratify_key"],
        random_state=RANDOM_STATE,
    )

    # Add augmented ONLY to train
    train_final = pd.concat([train_real, augmented_df], ignore_index=True)

    # Cleanup helper columns
    cleanup = ["body_hash", "stratify_key"]

    for df_ in [train_final, val_real, test_real]:
        for col in cleanup:
            if col in df_.columns:
                df_.drop(columns=[col], inplace=True)

    save_jsonl(train_final, OUT_DIR / "train.jsonl")
    save_jsonl(val_real, OUT_DIR / "val.jsonl")
    save_jsonl(test_real, OUT_DIR / "test.jsonl")

    print()
    print("Final dataset:")
    print(f"Train: {len(train_final)}")
    print(f"Val:   {len(val_real)}")
    print(f"Test:  {len(test_real)}")


if __name__ == "__main__":
    main()