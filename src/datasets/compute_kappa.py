"""
Phase 6.3 — Compute Cohen's Kappa between two annotators.

Reads  data/interim/gold_set_labels_you.csv
       data/interim/gold_set_labels_teammate.csv

Both CSVs must have columns: file, label
Labels must be one of: junk / spam / phishing / legitimate

Prints Kappa score and disagreement breakdown.
If Kappa < 0.75 → prints every disagreed email's file + both labels for review.

Usage:
    python src/compute_kappa.py
"""

import csv
from pathlib import Path
from sklearn.metrics import cohen_kappa_score

YOU_FILE      = Path("data/interim/gold_set_labels_you.csv")
TEAMMATE_FILE = Path("data/interim/gold_set_labels_teammate.csv")
VALID_LABELS  = {"junk", "spam", "phishing", "legitimate"}


def load_labels(path: Path) -> dict[str, str]:
    labels = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            label = row["label"].strip().lower()
            if label not in VALID_LABELS:
                raise ValueError(f"Invalid label '{label}' in {path} for file {row['file']}")
            labels[row["file"]] = label
    return labels


def main():
    you      = load_labels(YOU_FILE)
    teammate = load_labels(TEAMMATE_FILE)

    if you.keys() != teammate.keys():
        missing = you.keys() ^ teammate.keys()
        raise ValueError(f"File lists don't match. Mismatched entries: {missing}")

    files = list(you.keys())
    y_labels = [you[f] for f in files]
    t_labels = [teammate[f] for f in files]

    kappa = cohen_kappa_score(y_labels, t_labels)
    agreements   = sum(y == t for y, t in zip(y_labels, t_labels))
    disagreements = len(files) - agreements

    print(f"Total annotated : {len(files)}")
    print(f"Agreements      : {agreements} ({agreements/len(files):.1%})")
    print(f"Disagreements   : {disagreements} ({disagreements/len(files):.1%})")
    print(f"Cohen's Kappa   : {kappa:.4f}")
    print()

    if kappa >= 0.75:
        print("✅ Kappa ≥ 0.75 — labels are consistent. Proceed to Phase 7.")
    else:
        print(f"❌ Kappa < 0.75 — rules need refinement. Review disagreements below.")
        print()
        print("Disagreements (file | you | teammate):")
        for f, y, t in zip(files, y_labels, t_labels):
            if y != t:
                print(f"  {f}  |  you={y}  |  teammate={t}")


if __name__ == "__main__":
    main()
