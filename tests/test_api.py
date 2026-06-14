"""
test_api.py — FastAPI endpoint tests via TestClient.

Uses a MockPredictor injected via dependency override — no real model needed.
Covers: POST /triage (JSON + .eml), POST /feedback, GET /feedback/queue,
GET /health, GET /model/info, GET /metrics, error cases.
"""
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from src.inference.adapter import STRUCTURED_COLS
from src.inference.postprocess import TriageResponse as TriageDataclass
from tests.helpers import make_triage_response


# ---------------------------------------------------------------------------
# Patch the API's Predictor and FeedbackStore before importing the app
# ---------------------------------------------------------------------------

class _MockPredictor:
    def triage_json(self, data: dict) -> TriageDataclass:
        text = data.get("body_text", "") + data.get("subject", "")
        p = 0.95 if "phishing_signal" in text else 0.05
        label = "phishing" if p > 0.5 else "spam"
        return make_triage_response(
            label=label,
            predicted_class=label,
            phishing_probability=p,
            spam_probability=1 - p,
            trust_score=95.0,
        )

    def triage_eml(self, raw_bytes: bytes) -> TriageDataclass:
        return make_triage_response()

    def version(self) -> str:
        return "mock-v0.0"


@pytest.fixture
def client(tmp_path, monkeypatch):
    import src.serving.api as api_module
    from contextlib import asynccontextmanager

    # Disable lifespan (no real model artifacts in tests)
    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    api_module.app.router.lifespan_context = _noop_lifespan

    # Inject mock predictor
    api_module._predictor = _MockPredictor()
    api_module._manifest = {
        "version": "mock-v0.0",
        "model_type": "lightgbm",
        "training_date": "2026-05-31",
        "dataset_version": "model_ready_v1",
        "metrics": {"phishing_recall": 0.98, "accuracy": 0.97},
    }
    # Reset counters between tests
    api_module._counters = {"spam": 0, "phishing": 0, "analyst_review": 0, "priority_analyst_review": 0}
    api_module._latencies = []
    api_module._override_count = 0

    # Redirect FeedbackStore to tmp DB
    from src.feedback import store as store_module
    original_db = store_module._DB_PATH
    store_module._DB_PATH = tmp_path / "test.db"

    with TestClient(api_module.app, raise_server_exceptions=True) as c:
        yield c

    store_module._DB_PATH = original_db


# ---------------------------------------------------------------------------
# POST /triage — JSON
# ---------------------------------------------------------------------------

def test_triage_json_returns_200(client):
    resp = client.post("/triage", json={"subject": "Test", "body_text": "Hello"})
    assert resp.status_code == 200


def test_triage_json_response_schema(client):
    resp = client.post("/triage", json={"subject": "Test", "body_text": "Hello"})
    data = resp.json()
    for field in ("email_id", "label", "predicted_class", "spam_probability",
                  "phishing_probability", "trust_score", "routed_to_review",
                  "security_override", "reasons", "confidence_notes", "model_version", "latency_ms"):
        assert field in data, f"Missing field: {field}"


def test_triage_json_phishing_signal_routed_phishing(client):
    resp = client.post("/triage", json={"subject": "phishing_signal", "body_text": ""})
    assert resp.json()["label"] == "phishing"


def test_triage_json_spam_signal_routed_spam(client):
    resp = client.post("/triage", json={"subject": "Buy now", "body_text": "Promo offer"})
    assert resp.json()["label"] == "spam"


def test_triage_json_probabilities_sum_to_one(client):
    resp = client.post("/triage", json={"subject": "Test", "body_text": "Hello"})
    data = resp.json()
    total = data["spam_probability"] + data["phishing_probability"]
    assert abs(total - 1.0) < 0.01


def test_triage_eml_accepted(client):
    raw_eml = b"From: test@example.com\r\nSubject: Test\r\n\r\nBody text here"
    resp = client.post("/triage", content=raw_eml, headers={"content-type": "message/rfc822"})
    assert resp.status_code == 200


def test_triage_empty_body_accepted(client):
    resp = client.post("/triage", json={"subject": "", "body_text": ""})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /feedback
# ---------------------------------------------------------------------------

def test_feedback_accepted_for_known_email(client):
    # First triage to create a record
    triage_resp = client.post("/triage", json={"subject": "Test", "body_text": "Hello"})
    email_id = triage_resp.json()["email_id"]

    resp = client.post("/feedback", json={
        "email_id": email_id,
        "analyst_label": "Phishing",
        "analyst_id": "analyst-1",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"
    assert resp.json()["email_id"] == email_id


def test_feedback_404_for_unknown_email(client):
    resp = client.post("/feedback", json={
        "email_id": "does-not-exist",
        "analyst_label": "Phishing",
        "analyst_id": "analyst-1",
    })
    assert resp.status_code == 404


def test_feedback_optional_notes(client):
    triage_resp = client.post("/triage", json={"subject": "Test", "body_text": "Hello"})
    email_id = triage_resp.json()["email_id"]
    resp = client.post("/feedback", json={
        "email_id": email_id,
        "analyst_label": "Spam",
        "analyst_id": "analyst-1",
        "notes": "Looks like newsletter",
    })
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /feedback/queue
# ---------------------------------------------------------------------------

def test_queue_empty_initially(client):
    resp = client.get("/feedback/queue")
    assert resp.status_code == 200
    assert resp.json() == []


def test_queue_pagination_params_accepted(client):
    resp = client.get("/feedback/queue?limit=10&offset=0")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_returns_model_version(client):
    resp = client.get("/health")
    assert resp.json()["model_version"] == "mock-v0.0"


# ---------------------------------------------------------------------------
# GET /model/info
# ---------------------------------------------------------------------------

def test_model_info_fields_present(client):
    resp = client.get("/model/info")
    assert resp.status_code == 200
    data = resp.json()
    for field in ("model_version", "model_type", "training_date", "dataset_version", "metrics"):
        assert field in data


def test_model_info_metrics_populated(client):
    resp = client.get("/model/info")
    assert resp.json()["metrics"]["phishing_recall"] == 0.98


# ---------------------------------------------------------------------------
# GET /metrics
# ---------------------------------------------------------------------------

def test_metrics_returns_plain_text(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]


def test_metrics_contains_expected_keys(client):
    resp = client.get("/metrics")
    text = resp.text
    assert "emails_triaged_total" in text
    assert "analyst_review_rate" in text
    assert "override_rate" in text
    assert "inference_latency_ms" in text


def test_metrics_counts_increment_after_triage(client):
    client.post("/triage", json={"subject": "Test", "body_text": "Hello"})
    resp = client.get("/metrics")
    # At least one label bucket should be non-zero
    assert any(
        f'{label}" }} 1' in resp.text or f'label="{label}"}} 1' in resp.text
        or f'label="{label}"}} 1' in resp.text
        for label in ("spam", "phishing")
    )
