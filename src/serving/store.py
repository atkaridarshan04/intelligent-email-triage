"""
SQLite store for predictions and analyst feedback.
Used for continual learning — analyst verdicts are the retraining signal.
"""
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path("data/predictions.db")


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id                  TEXT PRIMARY KEY,
                timestamp           TEXT,
                eml_hash            TEXT,
                subject             TEXT,
                body_text           TEXT,
                sender_display_name TEXT,
                url_token_text      TEXT,
                spf_result          TEXT,
                dkim_result         TEXT,
                dmarc_result        TEXT,
                url_count           INTEGER,
                attachment_count    INTEGER,
                reply_to_mismatch   INTEGER,
                html_text_ratio     REAL,
                tld_risk_score      REAL,
                sender_seen_before  INTEGER,
                first_time_domain   INTEGER,
                predicted_label     TEXT,
                spam_prob           REAL,
                junk_prob           REAL,
                phishing_prob       REAL,
                trust_score         REAL,
                risk_score          INTEGER,
                active_signals      TEXT,
                analyst_verdict     TEXT,
                feedback_at         TEXT
            )
        """)


def save_prediction(eml_hash: str, features: dict[str, Any], result: dict[str, Any]) -> str:
    pred_id = str(uuid.uuid4())
    probs = result["class_probabilities"]
    with _conn() as con:
        con.execute("""
            INSERT INTO predictions VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
            )
        """, (
            pred_id,
            datetime.now(timezone.utc).isoformat(),
            eml_hash,
            features.get("subject"),
            features.get("body_text"),
            features.get("sender_display_name"),
            features.get("url_token_text"),
            features.get("spf_result"),
            features.get("dkim_result"),
            features.get("dmarc_result"),
            features.get("url_count"),
            features.get("attachment_count"),
            int(features.get("reply_to_mismatch", False)),
            features.get("html_text_ratio"),
            features.get("tld_risk_score"),
            int(features.get("sender_seen_before", False)),
            int(features.get("first_time_domain", True)),
            result["label"],
            probs.get("spam"),
            probs.get("junk"),
            probs.get("phishing"),
            result["trust_score"],
            result["risk_score"],
            ",".join(result.get("active_signals", [])),
            None,
            None,
        ))
    return pred_id


def save_feedback(pred_id: str, verdict: str) -> bool:
    with _conn() as con:
        cur = con.execute(
            "UPDATE predictions SET analyst_verdict=?, feedback_at=? WHERE id=?",
            (verdict, datetime.now(timezone.utc).isoformat(), pred_id)
        )
    return cur.rowcount > 0
