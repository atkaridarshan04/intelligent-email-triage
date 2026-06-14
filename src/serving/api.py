"""
api.py — FastAPI application.

Endpoints:
  POST /triage        — triage a reported email
  POST /feedback      — submit analyst verdict
  GET  /feedback/queue — emails awaiting review
  GET  /health
  GET  /model/info
  GET  /metrics       — Prometheus-format
"""
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from src.serving.schemas import (
    FeedbackRequest, FeedbackResponse,
    HealthResponse, ModelInfoResponse,
    QueueItem, TriageRequest, TriageResponse,
)

# ---------------------------------------------------------------------------
# App lifecycle — load predictor once at startup
# ---------------------------------------------------------------------------

_predictor = None  # type: ignore[var-annotated]
_manifest: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _predictor, _manifest
    from src.inference.predictor import Predictor
    _predictor = Predictor()
    manifest_path = Path(__file__).parents[2] / "checkpoints" / "production" / "manifest.json"
    _manifest = json.loads(manifest_path.read_text())
    yield


app = FastAPI(title="Intelligent Email Triage", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Metrics counters (in-memory, Prometheus-format on GET /metrics)
# ---------------------------------------------------------------------------

_counters: dict[str, int] = {"spam": 0, "phishing": 0, "analyst_review": 0, "priority_analyst_review": 0}
_latencies: list[float] = []
_feedback_count = 0
_override_count = 0


# ---------------------------------------------------------------------------
# POST /triage
# ---------------------------------------------------------------------------

@app.post("/triage", response_model=TriageResponse)
async def triage(request: Request):
    ct = request.headers.get("content-type", "")

    if "message/rfc822" in ct:
        raw = await request.body()
        result = _predictor.triage_eml(raw)
    else:
        body = await request.json()
        req = TriageRequest(**body)
        result = _predictor.triage_json({
            "subject": req.subject,
            "body_text": req.body_text,
            "sender_address": req.from_addr,
            "reply_to": req.reply_to,
            "urls": req.urls,
            "attachments": req.attachments,
        })

    # Update counters
    label_key = result.label.replace(" ", "_").lower()
    _counters[label_key] = _counters.get(label_key, 0) + 1
    _latencies.append(result.latency_ms)
    if result.security_override:
        _override_count += 1

    # Store in feedback store for review queue
    from src.feedback.store import FeedbackStore
    store = FeedbackStore()
    store.save_triage(result, subject=_extract_subject(request))

    return TriageResponse(**result.__dict__)


def _extract_subject(request: Request) -> str:
    # best-effort; subject is already in the triage response reasons if needed
    return ""


# ---------------------------------------------------------------------------
# POST /feedback
# ---------------------------------------------------------------------------

@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(req: FeedbackRequest):
    from src.feedback.store import FeedbackStore
    store = FeedbackStore()
    updated = store.record_verdict(
        email_id=req.email_id,
        analyst_label=req.analyst_label,
        analyst_id=req.analyst_id,
        notes=req.notes,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"email_id {req.email_id!r} not found")
    global _feedback_count
    _feedback_count += 1
    return FeedbackResponse(status="accepted", email_id=req.email_id)


# ---------------------------------------------------------------------------
# GET /feedback/queue
# ---------------------------------------------------------------------------

@app.get("/feedback/queue", response_model=list[QueueItem])
async def feedback_queue(limit: int = 50, offset: int = 0):
    from src.feedback.store import FeedbackStore
    store = FeedbackStore()
    rows = store.get_review_queue(limit=limit, offset=offset)
    return [QueueItem(**r) for r in rows]


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", model_version=_predictor.version())


# ---------------------------------------------------------------------------
# GET /model/info
# ---------------------------------------------------------------------------

@app.get("/model/info", response_model=ModelInfoResponse)
async def model_info():
    return ModelInfoResponse(
        model_version=_manifest.get("version", ""),
        model_type=_manifest.get("model_type", ""),
        training_date=_manifest.get("training_date", ""),
        dataset_version=_manifest.get("dataset_version", ""),
        metrics=_manifest.get("metrics", {}),
    )


# ---------------------------------------------------------------------------
# GET /metrics  (Prometheus text format)
# ---------------------------------------------------------------------------

@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    total = sum(_counters.values())
    review = _counters.get("analyst_review", 0) + _counters.get("priority_analyst_review", 0)
    review_rate = review / total if total else 0.0
    override_rate = _override_count / total if total else 0.0

    sorted_lat = sorted(_latencies)
    p50 = sorted_lat[len(sorted_lat) // 2] if sorted_lat else 0.0
    p99 = sorted_lat[int(len(sorted_lat) * 0.99)] if sorted_lat else 0.0

    lines = [
        f'emails_triaged_total{{label="spam"}} {_counters.get("spam", 0)}',
        f'emails_triaged_total{{label="phishing"}} {_counters.get("phishing", 0)}',
        f'emails_triaged_total{{label="analyst_review"}} {review}',
        f"analyst_review_rate {review_rate:.4f}",
        f"override_rate {override_rate:.4f}",
        f'inference_latency_ms{{quantile="0.5"}} {p50:.1f}',
        f'inference_latency_ms{{quantile="0.99"}} {p99:.1f}',
        f'model_version{{version="{_manifest.get("version", "")}"}} 1',
    ]
    return "\n".join(lines) + "\n"
