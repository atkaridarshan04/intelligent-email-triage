"""
schemas.py — Pydantic request/response models for the triage API.
"""
from typing import Optional
from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# POST /triage
# ---------------------------------------------------------------------------

class TriageRequest(BaseModel):
    """Pre-parsed email. Use POST /triage with Content-Type: message/rfc822 for raw .eml."""
    subject: str = ""
    body_text: str = ""
    from_addr: str = ""
    reply_to: str = ""
    urls: list[str] = []
    attachments: list[dict] = []  # [{filename, mime_type}]


class TriageResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    email_id: str
    label: str
    predicted_class: str
    spam_probability: float
    phishing_probability: float
    trust_score: float
    routed_to_review: bool
    security_override: bool
    reasons: list[str]
    confidence_notes: list[str]
    model_version: str
    latency_ms: float


# ---------------------------------------------------------------------------
# POST /feedback
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    email_id: str
    analyst_label: str          # "Spam" | "Phishing" | "Escalate" | "Defer"
    analyst_id: str
    notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    status: str
    email_id: str


# ---------------------------------------------------------------------------
# GET /feedback/queue item
# ---------------------------------------------------------------------------

class QueueItem(BaseModel):
    email_id: str
    subject: str
    trust_score: float
    predicted_class: str
    phishing_probability: float
    reasons: list[str]
    received_at: str


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    status: str
    model_version: str


# ---------------------------------------------------------------------------
# GET /model/info
# ---------------------------------------------------------------------------

class ModelInfoResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_version: str
    model_type: str
    training_date: str
    dataset_version: str
    metrics: dict
