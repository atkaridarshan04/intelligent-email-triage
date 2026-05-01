"""
Augment template-generated phishing samples in train.jsonl.

Strategy:
- Targets: source == 'augmented_template' (85.6% of phishing)
- Each targeted sample gets one augmentation applied at random:
    1. Word dropout     — randomly drop 10-15% of words
    2. Token shuffle    — shuffle words within a random sentence
    3. Subject prefix   — prepend a random noise prefix to subject
- Augmented copies are ADDED alongside originals (not replacing them)
- Augmentation rate: 50% of template samples get one copy added
- Output: data/processed/train_augmented.jsonl
  (val/test untouched)
"""

import json
import random
import re
from pathlib import Path

INPUT  = Path("data/processed/splits/train.jsonl")
OUTPUT = Path("data/processed/splits/train_augmented.jsonl")
SEED   = 42

SUBJECT_PREFIXES = ["Fwd:", "Re:", "FW:", "[Action Required]", "[Reminder]"]
DROPOUT_RATE     = (0.10, 0.15)
AUG_PROBABILITY  = 0.50  # fraction of template samples to augment


def word_dropout(text: str, rng: random.Random) -> str:
    rate = rng.uniform(*DROPOUT_RATE)
    words = text.split()
    kept = [w for w in words if rng.random() > rate]
    return " ".join(kept) if kept else text


def token_shuffle(text: str, rng: random.Random) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) < 2:
        words = text.split()
        if len(words) > 3:
            rng.shuffle(words)
            return " ".join(words)
        return text
    idx = rng.randrange(len(sentences))
    words = sentences[idx].split()
    if len(words) > 2:
        rng.shuffle(words)
        sentences[idx] = " ".join(words)
    return " ".join(sentences)


def subject_prefix(subject: str, rng: random.Random) -> str:
    prefix = rng.choice(SUBJECT_PREFIXES)
    return f"{prefix} {subject}"


AUGMENTATIONS = [word_dropout, token_shuffle]

rng = random.Random(SEED)
rows = [json.loads(l) for l in open(INPUT)]

augmented = []
for row in rows:
    if row.get("label") == "phishing" and row.get("source") == "augmented_template":
        if rng.random() < AUG_PROBABILITY:
            aug = dict(row)
            fn = rng.choice(AUGMENTATIONS)
            aug["body_text"] = fn(row["body_text"], rng)
            aug["subject"]   = subject_prefix(row["subject"], rng) if rng.random() < 0.4 else row["subject"]
            augmented.append(aug)

all_rows = rows + augmented
rng.shuffle(all_rows)

with open(OUTPUT, "w") as f:
    for row in all_rows:
        f.write(json.dumps(row) + "\n")

orig_phishing  = sum(1 for r in rows if r["label"] == "phishing")
aug_added      = len(augmented)
print(f"Original train : {len(rows)}")
print(f"Augmented added: {aug_added} (from {orig_phishing} phishing, {int(orig_phishing*0.856)} template)")
print(f"Total output   : {len(all_rows)}")
print(f"Written to {OUTPUT}")
