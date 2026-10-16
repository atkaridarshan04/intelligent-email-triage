"""
test_pipeline_integration.py — End-to-end pipeline tests (no HTTP, no real model).

Tests the full chain: MockAdapter → route → postprocess → store → drift.
Validates that all layers compose correctly and produce consistent outputs.
"""
import pytest
from tests.helpers import MockAdapter, make_triage_response
from src.inference.adapter import STRUCTURED_COLS, ModelOutput
from src.inference.threshold_router import route
from src.inference.postprocess import build_response
from src.feedback.store import FeedbackStore
from src.feedback.drift_detector import check_drift


@pytest.fixture
def store(tmp_path) -> FeedbackStore:
    return FeedbackStore(db_path=tmp_path / "test.db")


def _run_pipeline(adapter: MockAdapter, text: str, features: dict | None = None) :
    features = features or {col: 0.0 for col in STRUCTURED_COLS}
    out = adapter.predict(text, features)
    routing = route(out.spam_prob, out.phishing_prob, features)
    return build_response("test-id", out, routing, adapter.version()), out, routing


# ---------------------------------------------------------------------------
# Happy path — clear phishing
# ---------------------------------------------------------------------------

def test_clear_phishing_full_pipeline():
    adapter = MockAdapter()
    response, _, routing = _run_pipeline(adapter, "phishing_signal")

    assert response.label == "phishing"
    assert response.predicted_class == "phishing"
    assert response.phishing_probability > 0.9
    assert response.routed_to_review is False
    assert response.trust_score > 90
    assert response.model_version == "mock-v0.0"


# ---------------------------------------------------------------------------
# Happy path — clear spam
# ---------------------------------------------------------------------------

def test_clear_spam_full_pipeline():
    adapter = MockAdapter()
    response, _, _ = _run_pipeline(adapter, "buy now sale discount")

    assert response.label == "spam"
    assert response.spam_probability > 0.9
    assert response.routed_to_review is False


# ---------------------------------------------------------------------------
# Ambiguous — routes to review
# ---------------------------------------------------------------------------

def test_ambiguous_routes_to_review():
    adapter = MockAdapter(phishing_prob=0.52)
    response, _, routing = _run_pipeline(adapter, "")

    assert response.routed_to_review is True
    assert response.label in ("analyst_review", "priority_analyst_review")
    assert "analyst review" in " ".join(response.confidence_notes).lower()


# ---------------------------------------------------------------------------
# Security override overrides low trust
# ---------------------------------------------------------------------------

def test_security_override_escalates_borderline():
    adapter = MockAdapter(phishing_prob=0.72)
    features = {col: 0.0 for col in STRUCTURED_COLS}
    features["typosquatting_detected"] = 1.0

    out = adapter.predict("", features)
    routing = route(out.spam_prob, out.phishing_prob, features)
    response = build_response("test", out, routing, adapter.version())

    assert response.label == "phishing"
    assert response.security_override is True
    assert response.routed_to_review is False
    assert any("override" in n.lower() for n in response.confidence_notes)


# ---------------------------------------------------------------------------
# Pipeline → store → queue round trip
# ---------------------------------------------------------------------------

def test_review_email_appears_in_queue(store):
    adapter = MockAdapter(phishing_prob=0.52)
    features = {col: 0.0 for col in STRUCTURED_COLS}
    out = adapter.predict("", features)
    routing = route(out.spam_prob, out.phishing_prob, features)
    response = build_response("e-review-001", out, routing, adapter.version())

    store.save_triage(response, subject="Suspicious email")
    queue = store.get_review_queue()
    assert any(q["email_id"] == "e-review-001" for q in queue)


def test_auto_classified_email_not_in_queue(store):
    adapter = MockAdapter(phishing_prob=0.97)
    features = {col: 0.0 for col in STRUCTURED_COLS}
    out = adapter.predict("phishing_signal", features)
    routing = route(out.spam_prob, out.phishing_prob, features)
    response = build_response("e-auto-001", out, routing, adapter.version())

    store.save_triage(response)
    queue = store.get_review_queue()
    assert not any(q["email_id"] == "e-auto-001" for q in queue)


def test_analyst_verdict_removes_from_queue(store):
    adapter = MockAdapter(phishing_prob=0.52)
    features = {col: 0.0 for col in STRUCTURED_COLS}
    out = adapter.predict("", features)
    routing = route(out.spam_prob, out.phishing_prob, features)
    response = build_response("e-review-002", out, routing, adapter.version())

    store.save_triage(response)
    assert len(store.get_review_queue()) == 1

    store.record_verdict("e-review-002", "Phishing", "analyst-1")
    assert len(store.get_review_queue()) == 0


# ---------------------------------------------------------------------------
# Pipeline → store → drift full loop
# ---------------------------------------------------------------------------

def test_no_overrides_no_drift_trigger(store):
    import sqlite3
    from datetime import datetime, timedelta, timezone

    # 10 agreements in the last 7 days
    for i in range(10):
        reviewed_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        with sqlite3.connect(store._db) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO triage_log
                    (email_id, received_at, predicted_label, spam_prob, phishing_prob,
                     trust_score, routed_to_review, reasons,
                     analyst_label, analyst_id, reviewed_at, agreement)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (f"e-{i}", reviewed_at, "phishing", 0.05, 0.95, 90.0, 0, "[]",
                  "Phishing", "analyst-1", reviewed_at, 1))

    result = check_drift(store)
    assert result["trigger"] is False


def test_high_override_rate_triggers_drift(store):
    import sqlite3
    from datetime import datetime, timedelta, timezone

    for i in range(25):
        reviewed_at = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
        agreement = 1 if i < 5 else 0  # 20 overrides, 5 agreements = 80% override rate
        with sqlite3.connect(store._db) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO triage_log
                    (email_id, received_at, predicted_label, spam_prob, phishing_prob,
                     trust_score, routed_to_review, reasons,
                     analyst_label, analyst_id, reviewed_at, agreement)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (f"e-{i}", reviewed_at, "phishing", 0.05, 0.95, 90.0, 0, "[]",
                  "Spam" if agreement == 0 else "Phishing",
                  "analyst-1", reviewed_at, agreement))

    result = check_drift(store)
    assert result["trigger"] is True


# ---------------------------------------------------------------------------
# ModelOutput contract
# ---------------------------------------------------------------------------

def test_probabilities_sum_to_one():
    import numpy as np
    adapter = MockAdapter()
    features = {col: 0.0 for col in STRUCTURED_COLS}
    for text in ["phishing_signal", "buy now", "", "urgent action required"]:
        out = adapter.predict(text, features)
        assert abs(out.spam_prob + out.phishing_prob - 1.0) < 1e-6


def test_attributions_cover_all_structured_cols():
    adapter = MockAdapter()
    features = {col: 0.0 for col in STRUCTURED_COLS}
    out = adapter.predict("test", features)
    assert set(out.feature_attributions.keys()) == set(STRUCTURED_COLS)


def test_trust_score_always_valid():
    adapter = MockAdapter()
    features = {col: 0.0 for col in STRUCTURED_COLS}
    for p in [0.0, 0.1, 0.5, 0.9, 1.0]:
        out = ModelOutput(spam_prob=1 - p, phishing_prob=p, feature_attributions={})
        routing = route(out.spam_prob, out.phishing_prob, features)
        assert 0.0 <= routing.trust_score <= 100.0
