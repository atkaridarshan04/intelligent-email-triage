"""
test_feedback_store.py — Tests for SQLite feedback store.

All tests use an isolated in-memory DB via tmp_path — never touch data/feedback.db.

Covers: save_triage, record_verdict (agreement/override), review queue ordering,
queue excludes reviewed items, pagination, labeled feedback export, Defer exclusion.
"""
import pytest
from pathlib import Path
from tests.helpers import make_triage_response
from src.feedback.store import FeedbackStore


@pytest.fixture
def store(tmp_path) -> FeedbackStore:
    return FeedbackStore(db_path=tmp_path / "test.db")


def _review_response(email_id: str, trust: float = 60.0):
    return make_triage_response(
        email_id=email_id,
        label="analyst_review",
        predicted_class="phishing",
        trust_score=trust,
        routed_to_review=True,
    )


# ---------------------------------------------------------------------------
# save_triage
# ---------------------------------------------------------------------------

def test_save_triage_persists_record(store):
    r = make_triage_response()
    store.save_triage(r)
    import sqlite3
    conn = sqlite3.connect(store._db)
    row = conn.execute("SELECT * FROM triage_log WHERE email_id=?", (r.email_id,)).fetchone()
    conn.close()
    assert row is not None


def test_save_triage_idempotent(store):
    r = make_triage_response()
    store.save_triage(r)
    store.save_triage(r)  # duplicate — should not raise or duplicate
    import sqlite3
    conn = sqlite3.connect(store._db)
    count = conn.execute("SELECT COUNT(*) FROM triage_log WHERE email_id=?", (r.email_id,)).fetchone()[0]
    conn.close()
    assert count == 1


def test_save_triage_stores_correct_fields(store):
    r = make_triage_response(email_id="e-001", phishing_probability=0.95, trust_score=93.5)
    store.save_triage(r, subject="Test Subject", body_text="body text")
    import sqlite3
    conn = sqlite3.connect(store._db)
    row = conn.execute(
        "SELECT subject, phishing_prob, trust_score FROM triage_log WHERE email_id='e-001'"
    ).fetchone()
    conn.close()
    assert row[0] == "Test Subject"
    assert abs(row[1] - 0.95) < 0.001
    assert abs(row[2] - 93.5) < 0.001


# ---------------------------------------------------------------------------
# record_verdict
# ---------------------------------------------------------------------------

def test_record_verdict_returns_true_for_known_id(store):
    store.save_triage(make_triage_response(email_id="e-001"))
    result = store.record_verdict("e-001", "Phishing", "analyst-1")
    assert result is True


def test_record_verdict_returns_false_for_unknown_id(store):
    result = store.record_verdict("does-not-exist", "Phishing", "analyst-1")
    assert result is False


def test_agreement_set_when_labels_match(store):
    r = make_triage_response(email_id="e-001", predicted_class="phishing")
    store.save_triage(r)
    store.record_verdict("e-001", "phishing", "analyst-1")
    import sqlite3
    conn = sqlite3.connect(store._db)
    row = conn.execute("SELECT agreement FROM triage_log WHERE email_id='e-001'").fetchone()
    conn.close()
    assert row[0] == 1


def test_agreement_zero_when_labels_differ(store):
    r = make_triage_response(email_id="e-001", predicted_class="phishing")
    store.save_triage(r)
    store.record_verdict("e-001", "Spam", "analyst-1")
    import sqlite3
    conn = sqlite3.connect(store._db)
    row = conn.execute("SELECT agreement FROM triage_log WHERE email_id='e-001'").fetchone()
    conn.close()
    assert row[0] == 0


def test_verdict_stores_notes(store):
    store.save_triage(make_triage_response(email_id="e-001"))
    store.record_verdict("e-001", "Phishing", "analyst-1", notes="Clearly BEC")
    import sqlite3
    conn = sqlite3.connect(store._db)
    row = conn.execute("SELECT notes FROM triage_log WHERE email_id='e-001'").fetchone()
    conn.close()
    assert row[0] == "Clearly BEC"


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------

def test_queue_contains_only_routed_to_review(store):
    store.save_triage(make_triage_response(email_id="auto", routed_to_review=False, label="phishing"))
    store.save_triage(_review_response("review-1"))
    queue = store.get_review_queue()
    ids = [q["email_id"] for q in queue]
    assert "review-1" in ids
    assert "auto" not in ids


def test_queue_excludes_reviewed_items(store):
    store.save_triage(_review_response("r-001"))
    store.record_verdict("r-001", "Phishing", "analyst-1")
    queue = store.get_review_queue()
    assert not any(q["email_id"] == "r-001" for q in queue)


def test_queue_ordered_by_trust_score_ascending(store):
    store.save_triage(_review_response("low", trust=40.0))
    store.save_triage(_review_response("high", trust=70.0))
    store.save_triage(_review_response("mid", trust=55.0))
    queue = store.get_review_queue()
    scores = [q["trust_score"] for q in queue]
    assert scores == sorted(scores)


def test_queue_pagination(store):
    for i in range(5):
        store.save_triage(_review_response(f"e-{i:03d}", trust=float(50 + i)))
    page1 = store.get_review_queue(limit=2, offset=0)
    page2 = store.get_review_queue(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert {q["email_id"] for q in page1}.isdisjoint({q["email_id"] for q in page2})


def test_queue_returns_expected_fields(store):
    store.save_triage(_review_response("r-001"))
    queue = store.get_review_queue()
    assert len(queue) == 1
    item = queue[0]
    assert "email_id" in item
    assert "trust_score" in item
    assert "predicted_class" in item
    assert "phishing_probability" in item
    assert "reasons" in item
    assert "received_at" in item


def test_empty_queue_returns_empty_list(store):
    assert store.get_review_queue() == []


# ---------------------------------------------------------------------------
# Labeled feedback export
# ---------------------------------------------------------------------------

def test_labeled_feedback_returns_reviewed_records(store):
    store.save_triage(make_triage_response(email_id="e-001"), body_text="test body")
    store.record_verdict("e-001", "Phishing", "analyst-1")
    feedback = store.get_labeled_feedback()
    assert len(feedback) == 1
    assert feedback[0]["label"] == "phishing"


def test_labeled_feedback_excludes_unreviewed(store):
    store.save_triage(make_triage_response(email_id="e-001"))
    feedback = store.get_labeled_feedback()
    assert feedback == []


def test_labeled_feedback_excludes_defer(store):
    store.save_triage(make_triage_response(email_id="e-001"))
    store.record_verdict("e-001", "Defer", "analyst-1")
    feedback = store.get_labeled_feedback()
    assert feedback == []


def test_labeled_feedback_label_lowercased(store):
    store.save_triage(make_triage_response(email_id="e-001"))
    store.record_verdict("e-001", "Spam", "analyst-1")
    feedback = store.get_labeled_feedback()
    assert feedback[0]["label"] == "spam"
