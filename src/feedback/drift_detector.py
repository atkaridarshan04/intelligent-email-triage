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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = check_drift()
    print(result)
