"""
drift_detector.py — Rolling 7-day override rate monitor.

Logs a retrain trigger warning when override rate > 20%.
Does NOT auto-retrain — signals only. Human decides.

Usage (call from a periodic job or manually):
    python -m src.feedback.drift_detector
"""
import logging
from datetime import datetime, timedelta, timezone

from src.feedback.store import FeedbackStore

logger = logging.getLogger(__name__)
OVERRIDE_THRESHOLD = 0.20
WINDOW_DAYS = 7


def check_drift(store: FeedbackStore | None = None) -> dict:
    if store is None:
        store = FeedbackStore()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)).isoformat()

    import sqlite3
    conn = sqlite3.connect(store._db)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT agreement FROM triage_log
        WHERE reviewed_at >= ? AND analyst_label IS NOT NULL
          AND analyst_label NOT IN ('Defer')
    """, (cutoff,)).fetchall()
    conn.close()

    total = len(rows)
    if total == 0:
        return {"total_reviewed": 0, "override_rate": 0.0, "trigger": False}

    overrides = sum(1 for r in rows if r["agreement"] == 0)
    override_rate = overrides / total

    trigger = override_rate > OVERRIDE_THRESHOLD
    if trigger:
        logger.warning(
            "RETRAIN TRIGGER: override rate %.1f%% over last %d days "
            "(%d/%d verdicts). Run: python scripts/retrain.py",
            override_rate * 100, WINDOW_DAYS, overrides, total,
        )

    return {"total_reviewed": total, "override_rate": override_rate, "trigger": trigger}


def get_detailed_drift(store: FeedbackStore | None = None) -> dict:
    if store is None:
        store = FeedbackStore()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)).isoformat()

    import sqlite3
    conn = sqlite3.connect(store._db)
    conn.row_factory = sqlite3.Row

    # Reviews in 7-day window
    rows = conn.execute("""
        SELECT agreement, analyst_label, predicted_label FROM triage_log
        WHERE reviewed_at >= ? AND analyst_label IS NOT NULL
          AND analyst_label NOT IN ('Defer')
    """, (cutoff,)).fetchall()

    # All triage events in 7-day window
    recent_events = conn.execute("""
        SELECT predicted_label, trust_score, routed_to_review, phishing_prob FROM triage_log
        WHERE received_at >= ?
    """, (cutoff,)).fetchall()
    conn.close()

    total = len(rows)
    overrides = sum(1 for r in rows if r["agreement"] == 0)
    agreements = sum(1 for r in rows if r["agreement"] == 1)
    override_rate = (overrides / total) if total > 0 else 0.0
    trigger = override_rate > OVERRIDE_THRESHOLD

    # Traffic distribution
    event_count = len(recent_events)
    phishing_count = sum(1 for r in recent_events if r["predicted_label"] == "phishing")
    spam_count = sum(1 for r in recent_events if r["predicted_label"] == "spam")
    review_count = sum(1 for r in recent_events if r["routed_to_review"] == 1)
    avg_trust = (sum(r["trust_score"] for r in recent_events) / event_count) if event_count > 0 else 100.0

    status = "DRIFT_ALERT" if trigger else "HEALTHY"
    if total == 0:
        recommendation = "No analyst reviews in the 7-day window. Operating on nominal baseline."
    elif trigger:
        recommendation = f"ACTION REQUIRED: Analyst override rate ({override_rate * 100:.1f}%) exceeds safety threshold ({OVERRIDE_THRESHOLD * 100:.0f}%). Model retraining recommended."
    else:
        recommendation = f"Model is performing stably. Override rate ({override_rate * 100:.1f}%) is within safe operational limits."

    return {
        "status": status,
        "trigger": trigger,
        "window_days": WINDOW_DAYS,
        "override_threshold": OVERRIDE_THRESHOLD,
        "total_reviewed": total,
        "overrides": overrides,
        "agreements": agreements,
        "override_rate": round(override_rate * 100, 1),
        "recommendation": recommendation,
        "recent_traffic": {
            "total_triaged_7d": event_count,
            "phishing_ratio": round((phishing_count / event_count * 100) if event_count else 0.0, 1),
            "spam_ratio": round((spam_count / event_count * 100) if event_count else 0.0, 1),
            "review_ratio": round((review_count / event_count * 100) if event_count else 0.0, 1),
            "avg_trust_score": round(avg_trust, 1),
        },
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = check_drift()
    print(result)
