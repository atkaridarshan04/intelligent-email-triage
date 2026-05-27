"""
deduplication.py — Exact + near-duplicate removal across all parsed records.

Strategy (from dataset-plan.md):
  - Exact: sha256(subject + body_text[:500])  — via pre-computed rec.id
  - Near-duplicate: MinHash LSH, Jaccard ~0.85
  - On collision: keep higher-quality source (Nazario > IWSPA-AP > Kaggle > others)

Memory design:
  - Exact dedup uses only rec.id strings (no body kept in dict values until winner chosen)
  - MinHash computed on-the-fly and discarded; only the LSH index is retained
  - num_perm=64 (sufficient for 0.85 threshold, halves LSH memory vs 128)
"""
import re
from collections import defaultdict

from datasketch import MinHash, MinHashLSH

from src.datasets.schema import EmailRecord

_NUM_PERM = 64  # 64 perms ≈ ±0.03 Jaccard error at threshold 0.85 — acceptable

# Source quality priority (lower index = higher quality)
_SOURCE_PRIORITY = ["nazario", "iwspa", "spamassassin", "trec", "ceas", "kaggle", "synthetic"]


def _source_rank(source: str) -> int:
    s = source.lower()
    for i, name in enumerate(_SOURCE_PRIORITY):
        if name in s:
            return i
    return len(_SOURCE_PRIORITY)


def _shingles(text: str, k: int = 3) -> set[str]:
    text = re.sub(r'\s+', ' ', text.lower())[:1000]
    return {text[i:i+k] for i in range(len(text) - k + 1)}


def _minhash(text: str) -> MinHash:
    m = MinHash(num_perm=_NUM_PERM)
    for s in _shingles(text):
        m.update(s.encode("utf-8"))
    return m


def deduplicate(records: list[EmailRecord], jaccard_threshold: float = 0.85) -> list[EmailRecord]:
    """
    Remove exact and near-duplicate records.
    On collision, keep the record from the higher-quality source.
    """
    # --- Pass 1: exact deduplication by id ---
    # Store only (index, source_rank) per id to avoid holding duplicate bodies.
    best: dict[str, tuple[int, int]] = {}  # id -> (list_index, rank)
    for i, rec in enumerate(records):
        rank = _source_rank(rec.source)
        existing = best.get(rec.id)
        if existing is None or rank < existing[1]:
            best[rec.id] = (i, rank)

    # Rebuild deduped list in source-quality order (best sources first for LSH pass)
    deduped: list[EmailRecord] = [records[idx] for idx, _ in
                                   sorted(best.values(), key=lambda t: t[1])]

    # --- Pass 2: near-duplicate removal via MinHash LSH ---
    lsh = MinHashLSH(threshold=jaccard_threshold, num_perm=_NUM_PERM)
    kept: list[EmailRecord] = []

    for rec in deduped:
        m = _minhash(rec.subject + " " + rec.body_text)
        if lsh.query(m):
            # Near-duplicate of an already-kept (higher-quality) record — skip
            continue
        lsh.insert(rec.id, m)
        kept.append(rec)

    return kept
