"""
Phase 6.1 — Sample 500 emails from combined Junk pool for gold set validation.

Reads  data/interim/junk_candidates/junk_labeled.jsonl       (Enron, 7,639)
       data/interim/synthetic_junk/synthetic_junk_noised.jsonl (synthetic, 10,000)

Writes data/interim/gold_set_500.jsonl          — 500 sampled records (label field stripped)
       data/interim/gold_set_template.csv        — blank annotation template for both annotators

Sample is stratified: ~44% Enron (~220), ~56% synthetic (~280) — proportional to pool sizes.

Usage:
    python src/sample_gold_set.py
"""

import csv
import json
import random
from pathlib import Path

ENRON_FILE     = Path("data/interim/junk_candidates/junk_labeled.jsonl")
SYNTHETIC_FILE = Path("data/interim/synthetic_junk/synthetic_junk_noised.jsonl")
GOLD_OUT       = Path("data/interim/gold_set_500.jsonl")
TEMPLATE_OUT   = Path("data/interim/gold_set_template.csv")

TOTAL_SAMPLE   = 500
random.seed(42)


def load(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def main():
    enron     = load(ENRON_FILE)
    synthetic = load(SYNTHETIC_FILE)

    total_pool = len(enron) + len(synthetic)

    # Stratified sample proportional to pool sizes
    n_enron     = round(TOTAL_SAMPLE * len(enron) / total_pool)
    n_synthetic = TOTAL_SAMPLE - n_enron

    sampled_enron     = random.sample(enron, n_enron)
    sampled_synthetic = random.sample(synthetic, n_synthetic)
    gold = sampled_enron + sampled_synthetic
    random.shuffle(gold)  # mix so annotator doesn't see source pattern

    GOLD_OUT.parent.mkdir(parents=True, exist_ok=True)

    # Write gold set — strip weak label so annotators aren't anchored to it
    with open(GOLD_OUT, "w", encoding="utf-8") as f:
        for rec in gold:
            rec_copy = {k: v for k, v in rec.items()
                        if k not in ("label", "junk_score", "matched_signals")}
            f.write(json.dumps(rec_copy) + "\n")

    # Write blank annotation template
    with open(TEMPLATE_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "label"])  # label: junk / spam / phishing / legitimate
        for rec in gold:
            writer.writerow([rec["file"], ""])

    print(f"Gold set written : {len(gold)} records")
    print(f"  Enron          : {n_enron}")
    print(f"  Synthetic      : {n_synthetic}")
    print(f"Gold set file    : {GOLD_OUT}")
    print(f"Annotation template: {TEMPLATE_OUT}")
    print()
    print("Next steps:")
    print("  1. Copy gold_set_template.csv → gold_set_labels_you.csv")
    print("  2. Copy gold_set_template.csv → gold_set_labels_teammate.csv")
    print("  3. Each person fills their CSV independently (junk/spam/phishing/legitimate)")
    print("  4. Run: python src/compute_kappa.py")


if __name__ == "__main__":
    main()
