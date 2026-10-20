"""
balancing.py — Stratified sampling, manifest generation, and 70/15/15 split.

Rules (from dataset-plan.md):
  - Spam target: 6,000–10,000
  - Phishing target: 8,000–12,000
  - Synthetic cap: ≤ 25% of total
  - Era distribution: legacy ≤ 30%, mid ~40%, recent ≥ 30%
  - No single source > 40% of any class
  - Split: 70/15/15, stratified by class, temporally ordered where possible
"""
import random
from collections import defaultdict
from typing import NamedTuple

import pandas as pd

from src.data.schema import EmailRecord

# Targets
SPAM_TARGET = (6_000, 10_000)
PHISHING_TARGET = (8_000, 12_000)
SYNTHETIC_CAP = 0.25

ERA_CAPS = {"legacy": 0.30, "mid": 0.40, "recent": 0.30}
MAX_SOURCE_SHARE = 0.40

SPLIT_RATIOS = (0.70, 0.15, 0.15)


class SamplingResult(NamedTuple):
    train: list[EmailRecord]
    val: list[EmailRecord]
    test: list[EmailRecord]
    manifest: pd.DataFrame


def _stratified_sample(
    records: list[EmailRecord],
    target_min: int,
    target_max: int,
) -> list[EmailRecord]:
    """
    Sample records to hit target range while respecting era caps and source caps.
    Prefers real over synthetic. Temporally orders by era bucket for splitting.
    """
    target = (target_min + target_max) // 2

    # Group by (era_bucket, source, augmented)
    groups: dict[tuple, list[EmailRecord]] = defaultdict(list)
    for r in records:
        groups[(r.era_bucket, r.source, r.augmented)].append(r)

    # Shuffle within each group
    for g in groups.values():
        random.shuffle(g)

    # Era budget
    era_budget = {era: int(target * cap) for era, cap in ERA_CAPS.items()}
    # Cap unknown-era records to leave room for recent synthetic samples.
    # Without this, unknown-era organic records fill target_max before synthetic recent gets a turn.
    era_budget["unknown"] = int(target * 0.60)  # unknown can fill at most 60%, preserving 40% for known eras

    # Source budget
    source_budget: dict[str, int] = defaultdict(lambda: int(target * MAX_SOURCE_SHARE))

    selected: list[EmailRecord] = []
    era_counts: dict[str, int] = defaultdict(int)
    source_counts: dict[str, int] = defaultdict(int)
    synthetic_count = 0

    # Two passes: real first, then synthetic to fill gap
    for augmented in [False, True]:
        for (era, source, aug), group in groups.items():
            if aug != augmented:
                continue
            for rec in group:
                if len(selected) >= target_max:
                    break
                if era_counts[era] >= era_budget.get(era, target):
                    continue
                if source_counts[source] >= source_budget[source]:
                    continue
                syn_ratio = (synthetic_count + (1 if augmented else 0)) / max(len(selected) + 1, 1)
                if augmented and syn_ratio > SYNTHETIC_CAP:
                    continue
                selected.append(rec)
                era_counts[era] += 1
                source_counts[source] += 1
                if augmented:
                    synthetic_count += 1

    return selected


def _temporal_split(records: list[EmailRecord]) -> tuple[list, list, list]:
    """Split 70/15/15 with temporal ordering: legacy/mid → train, recent → test preference.
    Synthetic (augmented=True) records are split independently 70/15/15 so they don't
    all land in test due to era_order pushing 'recent' to the end.
    """
    organic = [r for r in records if not r.augmented]
    synthetic = [r for r in records if r.augmented]

    era_order = {"legacy": 0, "mid": 1, "recent": 2, "unknown": 1}
    organic_sorted = sorted(organic, key=lambda r: era_order.get(r.era_bucket, 1))

    def _slice(recs):
        n = len(recs)
        n_train = int(n * SPLIT_RATIOS[0])
        n_val = int(n * SPLIT_RATIOS[1])
        return recs[:n_train], recs[n_train:n_train + n_val], recs[n_train + n_val:]

    o_train, o_val, o_test = _slice(organic_sorted)

    # Synthetic split independently (shuffled, not temporally ordered)
    random.shuffle(synthetic)
    s_train, s_val, s_test = _slice(synthetic)

    return o_train + s_train, o_val + s_val, o_test + s_test


def build_dataset(all_records: list[EmailRecord]) -> SamplingResult:
    """
    Full pipeline: filter → sample → split → manifest.
    Drops records with missing_feature_count > 2.
    """
    # Drop low-quality records
    records = [r for r in all_records if r.missing_feature_count <= 3 and r.label in ("spam", "phishing")]

    spam = [r for r in records if r.label == "spam"]
    phishing = [r for r in records if r.label == "phishing"]

    spam_sample = _stratified_sample(spam, *SPAM_TARGET)
    phishing_sample = _stratified_sample(phishing, *PHISHING_TARGET)

    spam_train, spam_val, spam_test = _temporal_split(spam_sample)
    phishing_train, phishing_val, phishing_test = _temporal_split(phishing_sample)

    def _tag(recs: list[EmailRecord], split: str) -> list[EmailRecord]:
        for r in recs:
            r.split = split
        return recs

    train = _tag(spam_train + phishing_train, "train")
    val = _tag(spam_val + phishing_val, "val")
    test = _tag(spam_test + phishing_test, "test")

    random.shuffle(train)
    random.shuffle(val)

    manifest = _build_manifest(train + val + test)
    return SamplingResult(train=train, val=val, test=test, manifest=manifest)


def _build_manifest(records: list[EmailRecord]) -> pd.DataFrame:
    rows = [
        {
            "id": r.id,
            "source": r.source,
            "era_bucket": r.era_bucket,
            "subtype": r.subtype,
            "label": r.label,
            "augmented": r.augmented,
            "split": r.split,
        }
        for r in records
    ]
    return pd.DataFrame(rows)
