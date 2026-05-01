"""
Stratified 70/15/15 train/val/test split of dataset.jsonl.
Outputs: data/processed/train.jsonl, val.jsonl, test.jsonl
"""

import json
import random
from collections import defaultdict
from pathlib import Path

INPUT  = Path("data/processed/splits/dataset.jsonl")
SPLITS = {"train": 0.70, "val": 0.15, "test": 0.15}
SEED   = 42

rows_by_label = defaultdict(list)
for line in open(INPUT):
    row = json.loads(line)
    rows_by_label[row["label"]].append(row)

split_rows = {"train": [], "val": [], "test": []}

rng = random.Random(SEED)
for label, rows in rows_by_label.items():
    rng.shuffle(rows)
    n = len(rows)
    n_train = int(n * SPLITS["train"])
    n_val   = int(n * SPLITS["val"])
    split_rows["train"].extend(rows[:n_train])
    split_rows["val"].extend(rows[n_train:n_train + n_val])
    split_rows["test"].extend(rows[n_train + n_val:])

for split, rows in split_rows.items():
    rng.shuffle(rows)
    out = Path(f"data/processed/splits/{split}.jsonl")
    with open(out, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    counts = {}
    for row in rows:
        counts[row["label"]] = counts.get(row["label"], 0) + 1
    print(f"{split}: {len(rows)} total — {counts}")
