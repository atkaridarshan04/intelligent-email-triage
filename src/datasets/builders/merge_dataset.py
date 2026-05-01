"""
Merge spam, phishing, and junk into a single dataset.jsonl with 15 fields.
Output: data/processed/dataset.jsonl
"""

import json
import random
from pathlib import Path

FIELDS = [
    "subject", "body_text", "sender_display_name", "url_token_text",
    "spf_result", "dkim_result", "dmarc_result", "url_count", "attachment_count",
    "reply_to_mismatch", "html_text_ratio", "tld_risk_score",
    "sender_seen_before", "first_time_domain", "label",
    "source",  # carried for augmentation targeting; dropped before training
]

SOURCES = [
    "data/processed/enriched/spam_class_enriched.jsonl",
    "data/processed/enriched/phishing_class_enriched.jsonl",
    "data/processed/classes/junk_features.jsonl",
]

OUTPUT = Path("data/processed/splits/dataset.jsonl")

rows = []
for path in SOURCES:
    for line in open(path):
        row = json.loads(line)
        rows.append({k: row.get(k) for k in FIELDS})

random.seed(42)
random.shuffle(rows)

with open(OUTPUT, "w") as f:
    for row in rows:
        f.write(json.dumps(row) + "\n")

counts = {}
for row in rows:
    counts[row["label"]] = counts.get(row["label"], 0) + 1

print(f"Total: {len(rows)}")
for label, n in sorted(counts.items()):
    print(f"  {label}: {n}")
print(f"Written to {OUTPUT}")
