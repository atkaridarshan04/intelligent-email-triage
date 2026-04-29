"""
Deduplication across parsed JSONL files.
- Exact dedup: sha256(subject + body_text[:500])
- Near-dedup: MinHash LSH at Jaccard ~0.85
- On collision: keep higher-quality source (priority order defined below)
Outputs deduplicated JSONL per class.
"""

import json
import hashlib
from pathlib import Path
from datasketch import MinHash, MinHashLSH

BASE = Path(__file__).parent / "data"

# Source priority: lower index = higher quality (kept on collision)
SOURCE_PRIORITY = ["nazario", "spamassassin", "ceas08", "trec07", "spamassassin_hard_ham"]

INPUTS = {
    "spam": [
        BASE / "parsed/trec07_spam.jsonl",
        BASE / "parsed/spamassassin_spam.jsonl",
        BASE / "parsed/csv_spam.jsonl",
    ],
    "phishing": [
        BASE / "parsed/csv_phishing.jsonl",
    ],
}

OUTPUTS = {
    "spam":     BASE / "parsed/spam_deduped.jsonl",
    "phishing": BASE / "parsed/phishing_deduped.jsonl",
}

NUM_PERM = 128
JACCARD_THRESHOLD = 0.85


def source_rank(record):
    src = record.get("source", "")
    for s in SOURCE_PRIORITY:
        if src.startswith(s):
            return SOURCE_PRIORITY.index(s)
    return len(SOURCE_PRIORITY)


def make_minhash(text):
    m = MinHash(num_perm=NUM_PERM)
    for word in text.lower().split():
        m.update(word.encode("utf-8"))
    return m


def dedup_class(label, input_files, output_file):
    print(f"\n--- {label.upper()} ---")

    # Load all records
    records = []
    for f in input_files:
        if not f.exists():
            continue
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    print(f"Loaded: {len(records)}")

    # Sort by source quality so we keep best on collision
    records.sort(key=source_rank)

    exact_seen = {}   # hash -> index of kept record
    lsh = MinHashLSH(threshold=JACCARD_THRESHOLD, num_perm=NUM_PERM)
    kept = []
    exact_dups = 0
    near_dups = 0

    for i, rec in enumerate(records):
        key = rec.get("subject", "") + rec.get("body_text", "")[:500]
        h = hashlib.sha256(key.encode("utf-8", errors="replace")).hexdigest()

        # Exact dedup
        if h in exact_seen:
            exact_dups += 1
            continue

        # Near-dedup via MinHash LSH
        mh = make_minhash(key)
        results = lsh.query(mh)
        if results:
            near_dups += 1
            continue

        # Keep this record
        exact_seen[h] = i
        lsh.insert(str(i), mh)
        kept.append(rec)

    print(f"Exact dups removed: {exact_dups}")
    print(f"Near dups removed:  {near_dups}")
    print(f"Kept: {len(kept)}")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as out:
        for rec in kept:
            out.write(json.dumps(rec) + "\n")
    print(f"Output: {output_file}")


def main():
    for label, inputs in INPUTS.items():
        dedup_class(label, inputs, OUTPUTS[label])


if __name__ == "__main__":
    main()
