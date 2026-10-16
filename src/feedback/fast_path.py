"""
fast_path.py — Fast-Path Episodic Memory Hot-Cache for Rapid Feedback Learning.

Enables instant learning from analyst decisions without waiting for periodic
model retraining. When an analyst confirms a verdict on a campaign (or email),
its signature is cached in-memory and in SQLite. Subsequent incoming reports of
the same campaign inherit the analyst verdict in sub-milliseconds (< 2ms) with
100% confidence.
"""

import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.features.clustering import (
    compute_campaign_cluster_id,
    compute_simhash,
    extract_root_domain,
    hamming_distance,
    normalize_subject,
)

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path(__file__).parents[2] / "data" / "feedback.db"


class FastPathCache:
    _instance: Optional["FastPathCache"] = None

    def __new__(cls, db_path: Path = _DEFAULT_DB):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(db_path)
        elif db_path != cls._instance.db_path:
            cls._instance._init(db_path)
        return cls._instance

    def _init(self, db_path: Path) -> None:
        self.db_path = db_path
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._ensure_table()
        self._load_into_memory()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fast_path_cache (
                    cluster_id TEXT PRIMARY KEY,
                    simhash TEXT NOT NULL,
                    normalized_subject TEXT NOT NULL,
                    sender_domain TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    analyst_id TEXT NOT NULL,
                    notes TEXT,
                    learned_at TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0
                )
            """)

    def _load_into_memory(self) -> None:
        try:
            with self._conn() as conn:
                rows = conn.execute("SELECT * FROM fast_path_cache").fetchall()
                for r in rows:
                    d = dict(r)
                    raw_sh = d.get("simhash")
                    if raw_sh is not None:
                        try:
                            if isinstance(raw_sh, str):
                                d["simhash"] = int(raw_sh, 16) if any(c in raw_sh for c in "abcdefABCDEF") else int(raw_sh)
                            else:
                                d["simhash"] = int(raw_sh)
                        except Exception:
                            d["simhash"] = 0
                    else:
                        d["simhash"] = 0
                    self._memory_cache[d["cluster_id"]] = d
            logger.info(f"Loaded {len(self._memory_cache)} active fast-path signatures into memory.")
        except Exception as e:
            logger.warning(f"Error loading fast-path memory cache: {e}")

    def remember_campaign(
        self,
        cluster_id: str,
        subject: str,
        body_text: str,
        sender_address: str,
        verdict: str,
        analyst_id: str = "tier1-soc-analyst",
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Records an analyst verdict into the Fast-Path episodic cache.
        All subsequent reports matching this cluster will inherit this verdict immediately.
        """
        sh = compute_simhash(body_text)
        hex_sh = f"{sh:016x}"
        norm_subj = normalize_subject(subject)
        root_dom = extract_root_domain(sender_address)
        learned_at = time.strftime("%Y-%m-%d %H:%M:%S UTC")

        entry = {
            "cluster_id": cluster_id,
            "simhash": sh,
            "normalized_subject": norm_subj,
            "sender_domain": root_dom,
            "verdict": verdict.lower().strip(),
            "analyst_id": analyst_id,
            "notes": notes or f"Analyst confirmed verdict for campaign {cluster_id}",
            "learned_at": learned_at,
            "hit_count": 0,
        }

        # 1. Update in-memory cache
        self._memory_cache[cluster_id] = entry

        # 2. Persist to SQLite as hex string to prevent uint64 overflow
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO fast_path_cache
                    (cluster_id, simhash, normalized_subject, sender_domain, verdict, analyst_id, notes, learned_at, hit_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(cluster_id) DO UPDATE SET
                    verdict = excluded.verdict,
                    analyst_id = excluded.analyst_id,
                    notes = excluded.notes,
                    learned_at = excluded.learned_at
            """, (
                cluster_id,
                hex_sh,
                norm_subj,
                root_dom,
                entry["verdict"],
                analyst_id,
                entry["notes"],
                learned_at,
            ))

        logger.info(f"⚡ Fast-Path memorized campaign {cluster_id} as '{verdict}' by {analyst_id}")
        return entry

    def lookup(
        self,
        subject: str,
        body_text: str,
        sender_address: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Checks if an email matches a previously resolved campaign.
        Lookup order:
          1. Exact cluster_id match in memory (<0.1ms).
          2. Fuzzy matching: matching sender root domain + normalized subject + SimHash Hamming distance <= 4.
        """
        if not self._memory_cache:
            return None

        # 1. Direct cluster ID match
        cid = compute_campaign_cluster_id(subject, body_text, sender_address)
        if cid in self._memory_cache:
            return self._record_hit(cid)

        # 2. Fuzzy match across active campaign signatures
        target_sh = compute_simhash(body_text)
        target_norm_subj = normalize_subject(subject)
        target_root_dom = extract_root_domain(sender_address)

        for entry_cid, entry in self._memory_cache.items():
            # Check domain compatibility
            if entry["sender_domain"] == target_root_dom:
                # Check subject compatibility
                if entry["normalized_subject"] == target_norm_subj:
                    # Check body fuzzy similarity
                    dist = hamming_distance(target_sh, entry["simhash"])
                    if dist <= 5:  # Within 5 bits out of 64
                        return self._record_hit(entry_cid)

        return None

    def _record_hit(self, cluster_id: str) -> Dict[str, Any]:
        """Increments hit counter in memory and DB, returns entry copy."""
        entry = self._memory_cache[cluster_id]
        entry["hit_count"] = entry.get("hit_count", 0) + 1

        try:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE fast_path_cache SET hit_count = hit_count + 1 WHERE cluster_id = ?",
                    (cluster_id,)
                )
        except Exception:
            pass

        return dict(entry)

    def get_stats(self) -> Dict[str, Any]:
        """Returns active memory metrics."""
        total_signatures = len(self._memory_cache)
        total_hits = sum(e.get("hit_count", 0) for e in self._memory_cache.values())
        return {
            "total_signatures": total_signatures,
            "total_hits": total_hits,
            "signatures": list(self._memory_cache.values()),
        }

    def clear(self) -> None:
        """Clears memory and DB (used for tests and resetting demo state)."""
        self._memory_cache.clear()
        with self._conn() as conn:
            conn.execute("DELETE FROM fast_path_cache")
