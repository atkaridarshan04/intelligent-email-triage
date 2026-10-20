"""
store.py — SQLite feedback store.

Schema stores both body_text (for future transformer retraining) and
features JSON (for LightGBM retraining). Postgres is a one-line config swap.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

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
                    agreement       INTEGER,    -- 1=agree, 0=override, NULL=pending
                    campaign_cluster_id TEXT,
                    sender_address  TEXT
                )
            """)
            # Schema migration check for existing databases
            cols = [col[1] for col in conn.execute("PRAGMA table_info(triage_log)").fetchall()]
            if "campaign_cluster_id" not in cols:
                conn.execute("ALTER TABLE triage_log ADD COLUMN campaign_cluster_id TEXT")
            if "sender_address" not in cols:
                conn.execute("ALTER TABLE triage_log ADD COLUMN sender_address TEXT")

    # ------------------------------------------------------------------
    # Write triage result (called by POST /triage)
    # ------------------------------------------------------------------

    def save_triage(
        self,
        result: TriageResponse,
        subject: str = "",
        body_text: str = "",
        features: Optional[dict] = None,
        sender_address: str = "",
        email_id: Optional[str] = None,
        campaign_cluster_id: Optional[str] = None,
    ) -> None:
        from src.features.clustering import compute_campaign_cluster_id
        email_id_to_use = email_id or result.email_id

        # Preserve existing cluster ID or supplied campaign_cluster_id
        cluster_id = campaign_cluster_id
        if not cluster_id and email_id_to_use:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT campaign_cluster_id FROM triage_log WHERE email_id = ?",
                    (email_id_to_use,)
                ).fetchone()
                if row and row["campaign_cluster_id"]:
                    cluster_id = row["campaign_cluster_id"]

        if not cluster_id:
            cluster_id = compute_campaign_cluster_id(subject, body_text, sender_address)

        is_wire_camp = "executive wire" in subject.lower() or "wire transfer authorization" in subject.lower()
        routed = 1 if (result.routed_to_review or "review" in getattr(result, "label", "").lower() or is_wire_camp) else 0
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO triage_log
                    (email_id, received_at, model_version, subject, body_text,
                     features, predicted_label, spam_prob, phishing_prob,
                     trust_score, routed_to_review, reasons, campaign_cluster_id, sender_address)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(email_id) DO UPDATE SET
                    received_at=excluded.received_at,
                    subject=excluded.subject,
                    body_text=excluded.body_text,
                    predicted_label=excluded.predicted_label,
                    spam_prob=excluded.spam_prob,
                    phishing_prob=excluded.phishing_prob,
                    trust_score=excluded.trust_score,
                    routed_to_review=excluded.routed_to_review,
                    campaign_cluster_id=excluded.campaign_cluster_id,
                    sender_address=excluded.sender_address
            """, (
                email_id_to_use,
                _now(),
                result.model_version,
                subject,
                body_text,
                json.dumps(features or {}),
                result.predicted_class,
                result.spam_probability,
                result.phishing_probability,
                result.trust_score,
                routed,
                json.dumps(result.reasons),
                cluster_id,
                sender_address,
            ))

    # ------------------------------------------------------------------
    # Write analyst verdict (called by POST /feedback or /verdict)
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
                "SELECT predicted_label, subject, body_text, sender_address, campaign_cluster_id FROM triage_log WHERE email_id = ?", (email_id,)
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

            # Automatically learn and seed Fast-Path memory
            try:
                from src.feedback.fast_path import FastPathCache
                from src.features.clustering import compute_campaign_cluster_id
                cid = row["campaign_cluster_id"] or compute_campaign_cluster_id(
                    row["subject"] or "", row["body_text"] or "", row["sender_address"] or ""
                )
                FastPathCache().remember_campaign(
                    cluster_id=cid,
                    subject=row["subject"] or "",
                    body_text=row["body_text"] or "",
                    sender_address=row["sender_address"] or "",
                    verdict=analyst_label,
                    analyst_id=analyst_id,
                    notes=notes,
                )
            except Exception:
                pass

        return True

    def record_bulk_verdicts(
        self,
        cluster_id: str,
        analyst_label: str,
        analyst_id: str = "tier1-soc-analyst",
        notes: Optional[str] = None,
    ) -> int:
        """
        Applies analyst verdict to ALL unreviewed reports in a campaign cluster simultaneously.
        Seeds Fast-Path Episodic Memory so future incoming reports inherit the verdict.
        Returns count of records updated.
        """
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT email_id, predicted_label, subject, body_text, sender_address
                FROM triage_log
                WHERE campaign_cluster_id = ? AND analyst_label IS NULL
            """, (cluster_id,)).fetchall()

            if not rows:
                return 0

            count = len(rows)
            now_ts = _now()
            for r in rows:
                agree = int(analyst_label.lower() == (r["predicted_label"] or "").lower())
                conn.execute("""
                    UPDATE triage_log
                    SET analyst_label=?, analyst_id=?, reviewed_at=?, notes=?, agreement=?
                    WHERE email_id=?
                """, (analyst_label, analyst_id, now_ts, notes or f"Bulk resolved campaign {cluster_id}", agree, r["email_id"]))

            # Seed Fast-Path memory with sample from this campaign
            try:
                from src.feedback.fast_path import FastPathCache
                rep = rows[0]
                FastPathCache().remember_campaign(
                    cluster_id=cluster_id,
                    subject=rep["subject"] or "",
                    body_text=rep["body_text"] or "",
                    sender_address=rep["sender_address"] or "",
                    verdict=analyst_label,
                    analyst_id=analyst_id,
                    notes=notes or f"Bulk resolved {count} reports for campaign {cluster_id}",
                )
            except Exception:
                pass

            return count

    # ------------------------------------------------------------------
    # Review queue (called by GET /feedback/queue and /app/queue)
    # ------------------------------------------------------------------

    def get_review_queue(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Return unreviewed emails ordered by trust_score ascending (most uncertain first)."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT email_id, subject, sender_address, trust_score, predicted_label,
                       phishing_prob, reasons, received_at, campaign_cluster_id
                FROM triage_log
                WHERE routed_to_review = 1 AND analyst_label IS NULL
                ORDER BY trust_score ASC
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()

        return [
            {
                "email_id": r["email_id"],
                "subject": r["subject"] or "(no subject)",
                "sender": r["sender_address"] or "unknown_sender",
                "trust_score": r["trust_score"],
                "predicted_class": r["predicted_label"],
                "phishing_probability": r["phishing_prob"],
                "reasons": json.loads(r["reasons"] or "[]"),
                "received_at": r["received_at"],
                "campaign_cluster_id": r["campaign_cluster_id"],
            }
            for r in rows
        ]

    def get_campaign_review_queue(self, limit: int = 50) -> list[dict]:
        """
        Groups pending review queue items into consolidated Campaign Incident Cards.
        Returns campaigns ordered by report volume DESC, then lowest trust score ASC.
        """
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT email_id, subject, body_text, sender_address, trust_score,
                       predicted_label, phishing_prob, reasons, received_at,
                       campaign_cluster_id
                FROM triage_log
                WHERE routed_to_review = 1 AND analyst_label IS NULL
                ORDER BY received_at DESC
            """).fetchall()

        if not rows:
            return []

        from src.features.clustering import compute_campaign_cluster_id

        campaigns: dict[str, dict] = {}
        for r in rows:
            cid = r["campaign_cluster_id"]
            if not cid:
                cid = compute_campaign_cluster_id(r["subject"] or "", r["body_text"] or "", r["sender_address"] or "")

            item = {
                "email_id": r["email_id"],
                "subject": r["subject"] or "(no subject)",
                "sender": r["sender_address"] or "unknown_sender",
                "trust_score": r["trust_score"] or 50.0,
                "predicted_class": r["predicted_label"] or "phishing",
                "phishing_probability": r["phishing_prob"] or 0.5,
                "reasons": json.loads(r["reasons"] or "[]"),
                "received_at": r["received_at"],
            }

            if cid not in campaigns:
                campaigns[cid] = {
                    "cluster_id": cid,
                    "subject": item["subject"],
                    "sender": item["sender"],
                    "count": 0,
                    "phishing_probs": [],
                    "trust_scores": [],
                    "first_seen": item["received_at"],
                    "last_seen": item["received_at"],
                    "top_signal": item["reasons"][0] if item["reasons"] else "Boundary uncertainty",
                    "reports": [],
                }

            c = campaigns[cid]
            c["count"] += 1
            c["reports"].append(item)
            c["phishing_probs"].append(item["phishing_probability"])
            c["trust_scores"].append(item["trust_score"])
            if item["received_at"] < c["first_seen"]:
                c["first_seen"] = item["received_at"]
            if item["received_at"] > c["last_seen"]:
                c["last_seen"] = item["received_at"]

        result = []
        for cid, c in campaigns.items():
            avg_phish = sum(c["phishing_probs"]) / len(c["phishing_probs"])
            min_trust = min(c["trust_scores"])
            suggested = "phishing" if avg_phish >= 0.5 else "spam"
            severity = "CRITICAL" if avg_phish >= 0.85 else ("HIGH" if avg_phish >= 0.60 else "MEDIUM")
            result.append({
                "cluster_id": cid,
                "subject": c["subject"],
                "sender": c["sender"],
                "count": c["count"],
                "avg_phishing_prob": avg_phish,
                "min_trust_score": min_trust,
                "severity": severity,
                "suggested_label": suggested,
                "first_seen": c["first_seen"],
                "last_seen": c["last_seen"],
                "top_signal": c["top_signal"],
                "reports": c["reports"],
            })

        # Order campaigns by report volume DESC, then min trust ASC
        result.sort(key=lambda x: (x["count"], -x["min_trust_score"]), reverse=True)
        return result[:limit]

    def get_soc_roi_metrics(self) -> dict[str, Any]:
        """Calculates live executive operational ROI metrics for review reduction."""
        with self._conn() as conn:
            total_reports = conn.execute("SELECT COUNT(*) FROM triage_log").fetchone()[0]
            pending_reports = conn.execute("SELECT COUNT(*) FROM triage_log WHERE routed_to_review = 1 AND analyst_label IS NULL").fetchone()[0]
            auto_resolved = conn.execute("SELECT COUNT(*) FROM triage_log WHERE routed_to_review = 0").fetchone()[0]
            analyst_resolved = conn.execute("SELECT COUNT(*) FROM triage_log WHERE analyst_label IS NOT NULL").fetchone()[0]
            benign_resolved = conn.execute("SELECT COUNT(*) FROM triage_log WHERE analyst_label IN ('benign', 'legitimate') OR predicted_label = 'legitimate_benign'").fetchone()[0]
            
            pending_campaigns = conn.execute("""
                SELECT COUNT(DISTINCT CASE WHEN campaign_cluster_id IS NOT NULL AND campaign_cluster_id != '' THEN campaign_cluster_id ELSE email_id END)
                FROM triage_log
                WHERE routed_to_review = 1 AND analyst_label IS NULL
            """).fetchone()[0]

        compression_ratio = round(pending_reports / max(1, pending_campaigns), 1) if pending_reports > 0 else 1.0
        effort_saved_pct = round((1.0 - (pending_campaigns / max(1, pending_reports))) * 100, 1) if pending_reports > 1 else 0.0
        deflection_rate_pct = round((auto_resolved / max(1, total_reports)) * 100, 1) if total_reports > 0 else 0.0

        return {
            "total_reports": total_reports,
            "pending_reports": pending_reports,
            "pending_campaigns": pending_campaigns,
            "compression_ratio": compression_ratio,
            "effort_saved_pct": effort_saved_pct,
            "auto_resolved": auto_resolved,
            "deflection_rate_pct": deflection_rate_pct,
            "analyst_resolved": analyst_resolved,
            "benign_resolved": benign_resolved,
        }

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
            clauses.append("(email_id LIKE ? OR subject LIKE ? OR body_text LIKE ? OR campaign_cluster_id LIKE ? OR sender_address LIKE ?)")
            pat = f"%{search}%"
            params.extend([pat, pat, pat, pat, pat])
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
                       analyst_label, analyst_id, reviewed_at, notes, agreement,
                       campaign_cluster_id, sender_address
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
            benign = conn.execute("SELECT COUNT(*) FROM triage_log WHERE predicted_label = 'legitimate_benign' OR analyst_label IN ('benign', 'legitimate')").fetchone()[0]

        reviewed_eval = agreed + overridden
        agreement_rate = (agreed / reviewed_eval) if reviewed_eval > 0 else 1.0
        override_rate = (overridden / reviewed_eval) if reviewed_eval > 0 else 0.0

        return {
            "total_triaged": total,
            "phishing_count": phishing,
            "spam_count": spam,
            "benign_count": benign,
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
