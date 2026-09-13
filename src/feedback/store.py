"""
store.py — SQLite feedback store.

Schema stores both body_text (for future transformer retraining) and
features JSON (for LightGBM retraining). Postgres is a one-line config swap.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.inference.postprocess import TriageResponse

_DB_PATH = Path(__file__).parents[2] / "data" / "feedback.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FeedbackStore:
    def __init__(self, db_path: Optional[Path] = None):
        self._db = db_path if db_path is not None else _DB_PATH
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS triage_log (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id        TEXT NOT NULL UNIQUE,
                    received_at     TEXT NOT NULL,
                    model_version   TEXT,
                    subject         TEXT,
                    body_text       TEXT,
                    features        TEXT,       -- JSON
                    predicted_label TEXT,
                    spam_prob       REAL,
                    phishing_prob   REAL,
                    trust_score     REAL,
                    routed_to_review INTEGER,
                    reasons         TEXT,       -- JSON array
                    -- analyst verdict (populated on POST /feedback)
                    analyst_label   TEXT,
                    analyst_id      TEXT,
                    reviewed_at     TEXT,
                    notes           TEXT,
                    agreement       INTEGER     -- 1=agree, 0=override, NULL=pending
                )
            """)

    # ------------------------------------------------------------------
    # Write triage result (called by POST /triage)
    # ------------------------------------------------------------------

    def save_triage(
        self,
        result: TriageResponse,
        subject: str = "",
        body_text: str = "",
        features: Optional[dict] = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO triage_log
                    (email_id, received_at, model_version, subject, body_text,
                     features, predicted_label, spam_prob, phishing_prob,
                     trust_score, routed_to_review, reasons)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                result.email_id,
                _now(),
                result.model_version,
                subject,
                body_text,
                json.dumps(features or {}),
                result.predicted_class,
                result.spam_probability,
                result.phishing_probability,
                result.trust_score,
                int(result.routed_to_review),
                json.dumps(result.reasons),
            ))

    # ------------------------------------------------------------------
    # Write analyst verdict (called by POST /feedback)
    # ------------------------------------------------------------------

    def record_verdict(
        self,
        email_id: str,
        analyst_label: str,
        analyst_id: str,
        notes: Optional[str] = None,
    ) -> bool:
        """Returns True if record found and updated, False if email_id unknown."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT predicted_label FROM triage_log WHERE email_id = ?", (email_id,)
            ).fetchone()
            if row is None:
                return False

            agreement = int(
                analyst_label.lower() == (row["predicted_label"] or "").lower()
            )
            conn.execute("""
                UPDATE triage_log
                SET analyst_label=?, analyst_id=?, reviewed_at=?, notes=?, agreement=?
                WHERE email_id=?
            """, (analyst_label, analyst_id, _now(), notes, agreement, email_id))
        return True

    # ------------------------------------------------------------------
    # Review queue (called by GET /feedback/queue)
    # ------------------------------------------------------------------

    def get_review_queue(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Return unreviewed emails ordered by trust_score ascending (most uncertain first)."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT email_id, subject, trust_score, predicted_label,
                       phishing_prob, reasons, received_at
                FROM triage_log
                WHERE routed_to_review = 1 AND analyst_label IS NULL
                ORDER BY trust_score ASC
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()

        return [
            {
                "email_id": r["email_id"],
                "subject": r["subject"] or "(no subject)",
                "trust_score": r["trust_score"],
                "predicted_class": r["predicted_label"],
                "phishing_probability": r["phishing_prob"],
                "reasons": json.loads(r["reasons"] or "[]"),
                "received_at": r["received_at"],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Retraining data export (called by scripts/retrain.py)
    # ------------------------------------------------------------------

    def get_labeled_feedback(self) -> list[dict]:
        """Return all analyst-reviewed records for retraining."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT email_id, body_text, features, analyst_label, reviewed_at
                FROM triage_log
                WHERE analyst_label IS NOT NULL
                  AND analyst_label NOT IN ('Defer')
            """).fetchall()

        return [
            {
                "email_id": r["email_id"],
                "body_text": r["body_text"],
                "features": json.loads(r["features"] or "{}"),
                "label": r["analyst_label"].lower(),
                "reviewed_at": r["reviewed_at"],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Full Database Explorer & Audit Queries
    # ------------------------------------------------------------------

    def _build_filter_sql(self, search: str = "", label: str = "", status: str = "") -> tuple[str, list]:
        clauses = []
        params = []
        if search:
            clauses.append("(email_id LIKE ? OR subject LIKE ? OR body_text LIKE ?)")
            pat = f"%{search}%"
            params.extend([pat, pat, pat])
        if label:
            clauses.append("predicted_label = ?")
            params.append(label.lower())
        if status == "pending":
            clauses.append("routed_to_review = 1 AND analyst_label IS NULL")
        elif status == "agreed":
            clauses.append("agreement = 1")
        elif status == "overridden":
            clauses.append("agreement = 0")
        elif status == "reviewed":
            clauses.append("analyst_label IS NOT NULL")
        elif status == "review_needed":
            clauses.append("routed_to_review = 1")

        where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return where_sql, params

    def count_records(self, search: str = "", label: str = "", status: str = "") -> int:
        where_sql, params = self._build_filter_sql(search=search, label=label, status=status)
        with self._conn() as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM triage_log{where_sql}", params).fetchone()
            return row[0] if row else 0

    def get_all_records(
        self,
        limit: int = 50,
        offset: int = 0,
        search: str = "",
        label: str = "",
        status: str = "",
    ) -> list[dict]:
        where_sql, params = self._build_filter_sql(search=search, label=label, status=status)
        params.extend([limit, offset])
        with self._conn() as conn:
            rows = conn.execute(f"""
                SELECT id, email_id, received_at, model_version, subject, body_text,
                       features, predicted_label, spam_prob, phishing_prob,
                       trust_score, routed_to_review, reasons,
                       analyst_label, analyst_id, reviewed_at, notes, agreement
                FROM triage_log
                {where_sql}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """, params).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            d["reasons"] = json.loads(d.get("reasons") or "[]")
            feat_dict = json.loads(d.get("features") or "{}")
            if not feat_dict and (d.get("subject") or d.get("body_text")):
                try:
                    from src.data.schema import EmailRecord
                    from src.features.feature_pipeline import extract_features, _record_to_feature_dict
                    rec = EmailRecord(subject=d.get("subject", ""), body_text=d.get("body_text", ""))
                    extract_features(rec)
                    feat_dict = _record_to_feature_dict(rec)
                    conn.execute("UPDATE triage_log SET features = ? WHERE id = ?", (json.dumps(feat_dict), d["id"]))
                except Exception:
                    pass
            d["features"] = feat_dict
            results.append(d)
        return results

    def get_record_by_id(self, email_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM triage_log WHERE email_id = ?", (email_id,)
            ).fetchone()
            if row is None:
                return None
            d = dict(row)
            d["reasons"] = json.loads(d.get("reasons") or "[]")
            feat_dict = json.loads(d.get("features") or "{}")
            if not feat_dict and (d.get("subject") or d.get("body_text")):
                try:
                    from src.data.schema import EmailRecord
                    from src.features.feature_pipeline import extract_features, _record_to_feature_dict
                    rec = EmailRecord(subject=d.get("subject", ""), body_text=d.get("body_text", ""))
                    extract_features(rec)
                    feat_dict = _record_to_feature_dict(rec)
                    conn.execute("UPDATE triage_log SET features = ? WHERE id = ?", (json.dumps(feat_dict), d["id"]))
                except Exception:
                    pass
            d["features"] = feat_dict
            return d

    def get_stats(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM triage_log").fetchone()[0]
            phishing = conn.execute("SELECT COUNT(*) FROM triage_log WHERE predicted_label = 'phishing'").fetchone()[0]
            spam = conn.execute("SELECT COUNT(*) FROM triage_log WHERE predicted_label = 'spam'").fetchone()[0]
            routed_to_review = conn.execute("SELECT COUNT(*) FROM triage_log WHERE routed_to_review = 1").fetchone()[0]
            pending_review = conn.execute("SELECT COUNT(*) FROM triage_log WHERE routed_to_review = 1 AND analyst_label IS NULL").fetchone()[0]
            reviewed = conn.execute("SELECT COUNT(*) FROM triage_log WHERE analyst_label IS NOT NULL").fetchone()[0]
            agreed = conn.execute("SELECT COUNT(*) FROM triage_log WHERE agreement = 1").fetchone()[0]
            overridden = conn.execute("SELECT COUNT(*) FROM triage_log WHERE agreement = 0").fetchone()[0]
            deferred = conn.execute("SELECT COUNT(*) FROM triage_log WHERE analyst_label = 'Defer'").fetchone()[0]

        reviewed_eval = agreed + overridden
        agreement_rate = (agreed / reviewed_eval) if reviewed_eval > 0 else 1.0
        override_rate = (overridden / reviewed_eval) if reviewed_eval > 0 else 0.0

        return {
            "total_triaged": total,
            "phishing_count": phishing,
            "spam_count": spam,
            "routed_to_review": routed_to_review,
            "pending_review": pending_review,
            "reviewed_count": reviewed,
            "agreed_count": agreed,
            "overridden_count": overridden,
            "deferred_count": deferred,
            "agreement_rate": round(agreement_rate * 100, 1),
            "override_rate": round(override_rate * 100, 1),
        }

    def export_records_csv(self) -> str:
        import csv
        import io
        records = self.get_all_records(limit=10000, offset=0)
        output = io.StringIO()
        fieldnames = [
            "email_id", "received_at", "model_version", "subject",
            "predicted_label", "phishing_prob", "spam_prob", "trust_score",
            "routed_to_review", "analyst_label", "analyst_id", "reviewed_at",
            "agreement", "notes"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(r)
        return output.getvalue()
