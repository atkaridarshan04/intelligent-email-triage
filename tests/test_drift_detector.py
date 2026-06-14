"""
test_drift_detector.py — Tests for the override rate drift detector.

Uses an isolated tmp_path DB. Directly inserts DB rows to control
timestamps without waiting 7 days.
"""
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from src.feedback.drift_detector import check_drift, OVERRIDE_THRESHOLD, WINDOW_DAYS
from src.feedback.store import FeedbackStore
from tests.helpers import make_triage_response


@pytest.fixture
def store(tmp_path) -> FeedbackStore:
    return FeedbackStore(db_path=tmp_path / "test.db")


def _insert_verdict(store: FeedbackStore, email_id: str, agreement: int, days_ago: float = 1.0):
    """Directly insert a verdict row with a controlled timestamp."""
    reviewed_at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    with sqlite3.connect(store._db) as conn:
        conn.execute("""
            INSERT OR IGNORE INTO triage_log
                (email_id, received_at, predicted_label, spam_prob, phishing_prob,
                 trust_score, routed_to_review, reasons,
                 analyst_label, analyst_id, reviewed_at, agreement)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (email_id, reviewed_at, "phishing", 0.05, 0.95, 90.0, 0, "[]",
              "Phishing" if agreement else "Spam", "analyst-1", reviewed_at, agreement))


# ---------------------------------------------------------------------------

def test_empty_store_no_trigger(store):
    result = check_drift(store)
    assert result["trigger"] is False
    assert result["total_reviewed"] == 0
    assert result["override_rate"] == 0.0


def test_all_agree_no_trigger(store):
    for i in range(10):
        _insert_verdict(store, f"e-{i:03d}", agreement=1)
    result = check_drift(store)
    assert result["trigger"] is False
    assert result["override_rate"] == 0.0


def test_high_override_rate_triggers(store):
    # 21 overrides out of 100 = 21% > 20% threshold
    for i in range(79):
        _insert_verdict(store, f"agree-{i:03d}", agreement=1)
    for i in range(21):
        _insert_verdict(store, f"override-{i:03d}", agreement=0)
    result = check_drift(store)
    assert result["trigger"] is True
    assert result["override_rate"] > OVERRIDE_THRESHOLD


def test_exactly_at_threshold_no_trigger(store):
    # Exactly 20% — threshold is >, not >=
    for i in range(80):
        _insert_verdict(store, f"agree-{i:03d}", agreement=1)
    for i in range(20):
        _insert_verdict(store, f"override-{i:03d}", agreement=0)
    result = check_drift(store)
    assert result["trigger"] is False


def test_old_verdicts_outside_window_excluded(store):
    # All overrides but outside the 7-day window
    for i in range(30):
        _insert_verdict(store, f"old-{i:03d}", agreement=0, days_ago=8.0)
    result = check_drift(store)
    assert result["total_reviewed"] == 0
    assert result["trigger"] is False


def test_only_recent_verdicts_counted(store):
    # 30 old overrides (outside window) + 5 recent agreements
    for i in range(30):
        _insert_verdict(store, f"old-{i:03d}", agreement=0, days_ago=8.0)
    for i in range(5):
        _insert_verdict(store, f"new-{i:03d}", agreement=1, days_ago=1.0)
    result = check_drift(store)
    assert result["total_reviewed"] == 5
    assert result["trigger"] is False


def test_defer_verdicts_excluded(store):
    # Insert 30 Defer records — should not count toward override rate
    with sqlite3.connect(store._db) as conn:
        for i in range(30):
            reviewed_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            conn.execute("""
                INSERT OR IGNORE INTO triage_log
                    (email_id, received_at, predicted_label, spam_prob, phishing_prob,
                     trust_score, routed_to_review, reasons,
                     analyst_label, analyst_id, reviewed_at, agreement)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (f"defer-{i}", reviewed_at, "phishing", 0.05, 0.95, 90.0, 0, "[]",
                  "Defer", "analyst-1", reviewed_at, 0))
    result = check_drift(store)
    assert result["total_reviewed"] == 0


def test_returns_correct_counts(store):
    for i in range(7):
        _insert_verdict(store, f"agree-{i}", agreement=1)
    for i in range(3):
        _insert_verdict(store, f"over-{i}", agreement=0)
    result = check_drift(store)
    assert result["total_reviewed"] == 10
    assert abs(result["override_rate"] - 0.3) < 0.001
