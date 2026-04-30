"""
Phase 5 — Noise injection for synthetic Junk samples.

Reads  data/interim/synthetic_junk/synthetic_junk.jsonl
Writes data/interim/synthetic_junk/synthetic_junk_noised.jsonl

Base behavioral simulation was already done in Phase 3 (generate_synthetic_junk.py):
  sender_seen_before=False, first_time_domain=True, communication_frequency=0

Noise injection (applied here):
  ~15% of samples → first_time_domain flipped to False
  send_hour_deviation already uses Gaussian dist in Phase 3 — no change needed

Why: prevents model learning first_time_domain=True as a hard Junk rule.
In production, many legitimate first-contact senders exist.

Usage:
    python src/inject_noise.py
"""

import json
import random
from pathlib import Path

IN_FILE  = Path("data/interim/synthetic_junk/synthetic_junk.jsonl")
OUT_FILE = Path("data/interim/synthetic_junk/synthetic_junk_noised.jsonl")

NOISE_RATE = 0.15  # 15% get first_time_domain flipped to False

random.seed(42)


def main():
    records = []
    with open(IN_FILE, encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    total = len(records)
    noise_indices = set(random.sample(range(total), k=int(total * NOISE_RATE)))
    flipped = 0

    with open(OUT_FILE, "w", encoding="utf-8") as outf:
        for i, rec in enumerate(records):
            if i in noise_indices:
                rec["first_time_domain"] = False
                flipped += 1
            outf.write(json.dumps(rec) + "\n")

    print(f"Total records : {total:,}")
    print(f"first_time_domain flipped to False : {flipped:,} ({flipped/total:.1%})")
    print(f"Output: {OUT_FILE}")


if __name__ == "__main__":
    main()
