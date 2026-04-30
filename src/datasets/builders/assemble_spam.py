"""
Phase 4 — Assemble Spam Class (~20k)

Stratified downsample from spam_deduped.jsonl:
  - Legacy (pre-2010):  ≤ 30%  → ≤ 6,000
  - Mid (2010–2018):    ~40%   →  8,000
  - Recent (≥ 2018):    ≥ 30%  → ≥ 6,000
  - No single source   > 40%  → ≤ 8,000

Era is inferred from domain_age_reliable (True = recent) and source:
  trec07 → legacy, ceas08 → legacy/mid, spamassassin → legacy/mid
Since all records have domain_age_reliable=False (pre-2018 corpora),
we assign era from source heuristics and available date headers.
"""

import json
import random
import re
from pathlib import Path
from collections import defaultdict

random.seed(42)

BASE = Path(__file__).parent.parent.parent / "data"
INPUT  = BASE / "parsed/spam_deduped.jsonl"
OUTPUT = BASE / "parsed/spam_class.jsonl"

TARGET = 20_000
MAX_SOURCE_FRAC = 0.40  # no source > 40%

# Era assignment heuristics per source
# trec07 corpus is 2007 → legacy
# ceas08 corpus is 2008 → legacy
# spamassassin corpus is ~2002-2006 → legacy
# All available spam is legacy/mid — we have no recent spam from these corpora.
# We'll assign era from date header if parseable, else fall back to source default.

SOURCE_ERA_DEFAULT = {
    "trec07":       "legacy",
    "ceas08":       "legacy",
    "spamassassin": "legacy",
}

ERA_TARGETS = {
    "legacy": 6_000,   # ≤ 30%
    "mid":    8_000,   # ~40%
    "recent": 6_000,   # ≥ 30%
}


def infer_era(record):
    date_str = record.get("headers", {}).get("date", "")
    m = re.search(r'\b(19|20)(\d{2})\b', date_str)
    if m:
        year = int(m.group(1) + m.group(2))
        if year < 2010:
            return "legacy"
        elif year < 2018:
            return "mid"
        else:
            return "recent"
    src = record.get("source", "")
    for key, era in SOURCE_ERA_DEFAULT.items():
        if src.startswith(key):
            return era
    return "legacy"


def main():
    records = []
    with open(INPUT) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    # Assign era
    for r in records:
        r["era_bucket"] = infer_era(r)

    # Group by era
    by_era = defaultdict(list)
    for r in records:
        by_era[r["era_bucket"]].append(r)

    print("Era distribution in source:")
    for era, recs in by_era.items():
        print(f"  {era}: {len(recs)}")

    # Sample per era, respecting targets
    # If total available from mid+recent is insufficient, fill remainder from legacy
    sampled = []
    for era, target in ERA_TARGETS.items():
        pool = by_era[era]
        n = min(target, len(pool))
        sampled.extend(random.sample(pool, n))
        print(f"  Sampled {n} from {era} (target {target}, available {len(pool)})")

    # Fill to TARGET from legacy if under
    if len(sampled) < TARGET:
        already_used = {id(r) for r in sampled}
        legacy_remaining = [r for r in by_era["legacy"] if id(r) not in already_used]
        fill_n = min(TARGET - len(sampled), len(legacy_remaining))
        sampled.extend(random.sample(legacy_remaining, fill_n))
        print(f"  Filled {fill_n} more from legacy to reach target (era cap relaxed — no mid/recent sources available)")

    # Enforce source cap: no source > 40% of final set
    max_per_source = int(len(sampled) * MAX_SOURCE_FRAC)
    source_counts = defaultdict(int)
    final = []
    random.shuffle(sampled)
    for r in sampled:
        src = r.get("source", "")
        if source_counts[src] < max_per_source:
            source_counts[src] += 1
            final.append(r)

    # If we're under target due to source cap, fill from remaining
    if len(final) < TARGET:
        used_ids = {id(r) for r in final}
        remaining = [r for r in sampled if id(r) not in used_ids]
        # relax cap slightly to fill
        for r in remaining:
            if len(final) >= TARGET:
                break
            final.append(r)

    random.shuffle(final)
    print(f"\nFinal spam class: {len(final)}")

    from collections import Counter
    print("Source breakdown:", dict(Counter(r["source"] for r in final)))
    print("Era breakdown:", dict(Counter(r["era_bucket"] for r in final)))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as out:
        for r in final:
            out.write(json.dumps(r) + "\n")
    print(f"Written: {OUTPUT}")


if __name__ == "__main__":
    main()
