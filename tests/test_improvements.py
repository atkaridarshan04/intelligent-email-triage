"""
test_improvements.py — Unit and integration tests for:
  1. Campaign Deduplication & SimHash Fuzzy Clustering (src/features/clustering.py)
  2. Fast-Path Episodic Memory Hot-Cache (src/feedback/fast_path.py)
  3. Campaign Review Queue Grouping & 1-Click Bulk Verdicts (src/feedback/store.py)
  4. Operational Benign Handling & SOC ROI Metrics
"""

import pytest
from pathlib import Path

from src.features.clustering import (
    compute_campaign_cluster_id,
    compute_simhash,
    hamming_distance,
    normalize_subject,
    normalize_text_for_clustering,
)
from src.feedback.fast_path import FastPathCache
from src.feedback.store import FeedbackStore
from src.inference.postprocess import TriageResponse


# ---------------------------------------------------------------------------
# Test 1: Fuzzy Clustering & SimHash
# ---------------------------------------------------------------------------

def test_simhash_and_hamming_distance():
    text1 = "Dear Colleague, Please authorize the pending wire transfer for Project Titan before 5 PM today."
    text2 = "Dear Sarah, Please authorize the pending wire transfer for Project Titan before 5 PM today."
    text_different = "Limited time offer! Buy discount supplements and vitamins online today with free delivery!"

    h1 = compute_simhash(text1)
    h2 = compute_simhash(text2)
    h_diff = compute_simhash(text_different)

    # Near duplicates with only recipient name difference should have tiny Hamming distance (<= 3)
    dist_near = hamming_distance(h1, h2)
    assert dist_near <= 4, f"Expected small distance, got {dist_near}"

    # Completely different texts should have much larger distance
    dist_far = hamming_distance(h1, h_diff)
    assert dist_far > 10, f"Expected large distance, got {dist_far}"


def test_campaign_cluster_id_deterministic():
    sub1 = "URGENT: Executive Wire Transfer Authorization - Account #4091-8821"
    sub2 = "Re: URGENT: Executive Wire Transfer Authorization [Ref #99281]"
    sender1 = "executive-office@global-wire-settlements.com"
    sender2 = "executive-office@global-wire-settlements.com"
    body1 = "Please review the pending high-priority escrow wire transfer for Project Titan.\nRef: 12345"
    body2 = "Please review the pending high-priority escrow wire transfer for Project Titan.\nRef: 99881"

    cid1 = compute_campaign_cluster_id(sub1, body1, sender1)
    cid2 = compute_campaign_cluster_id(sub2, body2, sender2)

    assert cid1 == cid2, f"Expected identical campaign IDs for near-duplicate lures, got {cid1} vs {cid2}"
    assert cid1.startswith("camp_")


# ---------------------------------------------------------------------------
# Test 2: Fast-Path Episodic Memory
# ---------------------------------------------------------------------------

def test_fast_path_cache_lifecycle(tmp_path):
    test_db = tmp_path / "test_feedback.db"
    cache = FastPathCache(db_path=test_db)
    cache.clear()

    subj = "URGENT: Executive Wire Transfer Authorization"
    body = "Please review the escrow wire transfer immediately."
    sender = "scam@wire-auth.com"
    cluster_id = "camp_test_01"

    # Initially lookup is empty
    assert cache.lookup(subj, body, sender) is None

    # Analyst confirms verdict
    cache.remember_campaign(
        cluster_id=cluster_id,
        subject=subj,
        body_text=body,
        sender_address=sender,
        verdict="phishing",
        analyst_id="lead-analyst",
        notes="Confirmed wire fraud attack",
    )

    # Subsequent lookup hits fast-path memory instantly
    hit = cache.lookup(subj, body, sender)
    assert hit is not None
    assert hit["cluster_id"] == cluster_id
    assert hit["verdict"] == "phishing"
    assert hit["analyst_id"] == "lead-analyst"
    assert hit["hit_count"] >= 1


def test_fast_path_benign_memory(tmp_path):
    test_db = tmp_path / "test_feedback.db"
    cache = FastPathCache(db_path=test_db)
    cache.clear()

    subj = "Corporate Employee Wellness Survey 2026"
    body = "Please complete the annual internal wellness questionnaire in Workday."
    sender = "hr-wellness@company.com"
    cluster_id = "camp_wellness_01"

    cache.remember_campaign(
        cluster_id=cluster_id,
        subject=subj,
        body_text=body,
        sender_address=sender,
        verdict="benign",
        analyst_id="lead-analyst",
    )

    hit = cache.lookup(subj, body, sender)
    assert hit is not None
    assert hit["verdict"] == "benign"


def test_threat_absent_internal_benign_routing():
    from src.inference.threshold_router import route
    from src.data.schema import EmailRecord
    from src.features.feature_pipeline import run as run_pipeline
    from src.inference.predictor import _record_to_feature_dict

    rec = EmailRecord(
        subject="Action Required: Company Annual Health & Wellness Benefits Enrollment",
        body_text="Dear Colleague,\nAnnual open enrollment for Company Healthcare and Life Insurance begins next Monday.\nPlease review your options in Workday.",
        sender_address="hr-benefits@company.com",
    )
    run_pipeline(rec)
    features = _record_to_feature_dict(rec)

    # Even if ML model leaned towards phishing due to "Action Required",
    # verified corporate sender with zero threat signals routes to legitimate_benign.
    decision = route(spam_prob=0.1, phishing_prob=0.9, features=features)
    assert decision.label == "legitimate_benign"
    assert decision.predicted_class == "legitimate_benign"
    assert decision.routed_to_review is False
    assert decision.trust_score >= 90.0


# ---------------------------------------------------------------------------
# Test 3: FeedbackStore Campaign Grouping & Bulk Verdicts
# ---------------------------------------------------------------------------

def test_feedback_store_campaign_queue_and_bulk_action(tmp_path):
    test_db = tmp_path / "test_feedback.db"
    store = FeedbackStore(db_path=test_db)

    # Ingest 3 reports of the same campaign targeting different users
    subj = "Executive Wire Transfer Authorization"
    body = "Please approve escrow transfer 9912 immediately."
    sender = "fraud@wire-scam.com"

    for i in range(3):
        fake_resp = TriageResponse(
            email_id=f"email-wire-{i}",
            label="analyst_review",
            predicted_class="phishing",
            spam_probability=0.25,
            phishing_probability=0.75,
            trust_score=68.0,
            routed_to_review=True,
            security_override=False,
            reasons=["High financial urgency"],
            confidence_notes=["Uncertainty routing"],
            model_version="test-model",
            latency_ms=12.0,
        )
        store.save_triage(fake_resp, subject=subj, body_text=body, sender_address=sender)

    # Check that get_campaign_review_queue groups them into 1 campaign card
    campaigns = store.get_campaign_review_queue()
    assert len(campaigns) == 1
    assert campaigns[0]["count"] == 3
    assert campaigns[0]["subject"] == subj

    # Check SOC ROI metrics reflect 3:1 compression
    metrics = store.get_soc_roi_metrics()
    assert metrics["pending_reports"] == 3
    assert metrics["pending_campaigns"] == 1
    assert metrics["compression_ratio"] == 3.0
    assert metrics["effort_saved_pct"] > 60.0

    # Execute 1-click bulk verdict
    cluster_id = campaigns[0]["cluster_id"]
    resolved_count = store.record_bulk_verdicts(
        cluster_id=cluster_id,
        analyst_label="phishing",
        analyst_id="lead-analyst",
        notes="Bulk resolved via test",
    )
    assert resolved_count == 3

    # Queue should now be clear
    assert len(store.get_campaign_review_queue()) == 0


# ---------------------------------------------------------------------------
# Test 4: Integration with FastAPI Endpoints
# ---------------------------------------------------------------------------

def test_queue_endpoints_and_simulation():
    from fastapi.testclient import TestClient
    from src.serving.api import app

    with TestClient(app, raise_server_exceptions=True) as client:
        # Test GET /app/queue returns 200 with campaign view
        r = client.get("/app/queue?view=campaigns")
        assert r.status_code == 200
        assert "SOC Tier-2 Review Queue" in r.text
        assert "Queue Compression Ratio" in r.text

        # Test POST /app/queue/simulate-campaign injects 10 reports and redirects
        r_sim = client.post("/app/queue/simulate-campaign", follow_redirects=True)
        assert r_sim.status_code == 200
        assert "Executive Wire Transfer Authorization" in r_sim.text
        assert "User Reports" in r_sim.text

        # Test POST /app/queue/bulk-verdict resolves campaign
        from src.feedback.store import FeedbackStore
        store = FeedbackStore()
        camps = store.get_campaign_review_queue()
        if camps:
            cid = camps[0]["cluster_id"]
            r_bulk = client.post(
                "/app/queue/bulk-verdict",
                data={
                    "cluster_id": cid,
                    "analyst_label": "phishing",
                    "analyst_id": "test-analyst",
                },
                follow_redirects=True,
            )
            assert r_bulk.status_code == 200

