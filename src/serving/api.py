"""
api.py — Barclays Cyber Operations Intelligent Email Triage FastAPI application.

Endpoints:
  POST /triage                 — triage a reported email (JSON or RFC-822)
  POST /feedback               — submit SOC analyst verdict
  GET  /feedback/queue         — emails awaiting human review
  GET  /health                 — service liveness probe
  GET  /model/info             — active model governance metadata
  GET  /metrics                — Prometheus-format metrics
  GET  /                       — redirect to /app/
  GET  /api/database/records   — paginated & filtered audit log records
  GET  /api/database/stats     — feedback database summary statistics
  GET  /api/database/export    — export audit log as CSV or JSON
  GET  /api/drift/report       — 7-day rolling drift metrics
  POST /api/retrain/run        — execute retrain job (calibrate or full)
  POST /api/model/promote      — promote versioned checkpoint to production
  POST /api/model/reload       — hot-reload model predictor in memory
  GET  /api/model/phase3-status — Phase 3 RoBERTa deep neural status
"""
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse

from src.feedback.drift_detector import get_detailed_drift
from src.feedback.store import FeedbackStore
from src.models.transformer_model import get_phase3_status
from src.serving.schemas import (
    FeedbackRequest, FeedbackResponse,
    HealthResponse, ModelInfoResponse,
    QueueItem, TriageRequest, TriageResponse,
)

# ---------------------------------------------------------------------------
# App lifecycle — load predictor at startup with hot-reload capability
# ---------------------------------------------------------------------------

_predictor = None  # type: ignore[var-annotated]
_manifest: dict = {}


def reload_predictor() -> dict:
    global _predictor, _manifest
    from src.inference.predictor import Predictor
    _predictor = Predictor()
    manifest_path = Path(__file__).parents[2] / "checkpoints" / "production" / "manifest.json"
    if manifest_path.exists():
        _manifest = json.loads(manifest_path.read_text())
    return _manifest


@asynccontextmanager
async def lifespan(app: FastAPI):
    reload_predictor()
    yield


app = FastAPI(title="Barclays Intelligent Email Triage & SOC Defense Engine", lifespan=lifespan)

# Mount static files directory (/static/BCS.png)
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# Mount enterprise web interface at /app and legacy alias at /demo
from src.serving.demo import demo_router, ui_router  # noqa: E402
app.include_router(ui_router)
app.include_router(demo_router)


@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/app/", status_code=307)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icon_path = _STATIC_DIR / "BCS.png"
    if icon_path.exists():
        return FileResponse(str(icon_path), media_type="image/png")
    return Response(status_code=404)


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
    global _predictor
    if _predictor is None:
        reload_predictor()
    ct = request.headers.get("content-type", "")

    model_param = request.query_params.get("model")

    if "message/rfc822" in ct:
        raw = await request.body()
        result = _predictor.triage_eml(raw, model_choice=model_param)
        extracted_subject = ""
        extracted_body = ""
        import email as _email
        from email import policy as _policy
        try:
            msg = _email.message_from_bytes(raw, policy=_policy.default)
            extracted_subject = str(msg.get("Subject", ""))
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    extracted_body = part.get_content() or ""
                    break
        except Exception:
            pass
    else:
        body = await request.json()
        req = TriageRequest(**body)
        extracted_subject = req.subject
        extracted_body = req.body_text
        result = _predictor.triage_json({
            "subject": req.subject,
            "body_text": req.body_text,
            "sender_address": req.from_addr,
            "reply_to": req.reply_to,
            "urls": req.urls,
            "attachments": req.attachments,
        }, model_choice=req.model or model_param)

    # Update counters
    label_key = result.label.replace(" ", "_").lower()
    _counters[label_key] = _counters.get(label_key, 0) + 1
    _latencies.append(result.latency_ms)
    if result.security_override:
        _override_count += 1

    # Store in feedback store with actual subject, body & 19 extracted features
    store = FeedbackStore()
    store.save_triage(
        result,
        subject=extracted_subject,
        body_text=extracted_body,
        features=result.features,
    )

    return TriageResponse(**result.__dict__)


# ---------------------------------------------------------------------------
# POST /feedback
# ---------------------------------------------------------------------------

@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(req: FeedbackRequest):
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
    store = FeedbackStore()
    rows = store.get_review_queue(limit=limit, offset=offset)
    return [QueueItem(**r) for r in rows]


# ---------------------------------------------------------------------------
# Database Explorer API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/database/records")
async def api_database_records(
    limit: int = 50,
    offset: int = 0,
    search: str = "",
    label: str = "",
    status: str = "",
):
    store = FeedbackStore()
    records = store.get_all_records(limit=limit, offset=offset, search=search, label=label, status=status)
    total = store.count_records(search=search, label=label, status=status)
    return {"total": total, "limit": limit, "offset": offset, "records": records}


@app.get("/api/database/stats")
async def api_database_stats():
    return FeedbackStore().get_stats()


@app.get("/api/database/export")
async def api_database_export(format: str = "csv"):
    store = FeedbackStore()
    if format.lower() == "json":
        records = store.get_all_records(limit=10000, offset=0)
        return Response(
            content=json.dumps(records, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=triage_audit_log.json"},
        )
    csv_content = store.export_records_csv()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=triage_audit_log.csv"},
    )


# ---------------------------------------------------------------------------
# Drift Observability API Endpoint
# ---------------------------------------------------------------------------

@app.get("/api/drift/report")
async def api_drift_report():
    return get_detailed_drift()


# ---------------------------------------------------------------------------
# Training & Retraining Streaming API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/training/stream")
async def api_training_stream(
    mode: str = "scratch",
    data_dir: Optional[str] = None,
    version_tag: Optional[str] = None,
    auto_promote: bool = True,
):
    from fastapi.responses import StreamingResponse
    from src.training.engine import stream_training_pipeline

    def sse_event_generator():
        for event in stream_training_pipeline(
            mode=mode,
            data_dir_path=data_dir,
            version_tag=version_tag,
            auto_promote=auto_promote,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/training/datasets")
async def api_training_datasets():
    from src.training.engine import get_available_datasets
    return get_available_datasets()


@app.post("/api/training/upload-dataset")
async def api_training_upload_dataset(
    split: str = Form(...),
    file: UploadFile = File(...),
):
    from src.training.engine import BARCLAYS_DATA_DIR
    BARCLAYS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest_file = BARCLAYS_DATA_DIR / f"{split}.jsonl"
    content = await file.read()
    dest_file.write_bytes(content)
    return {
        "status": "uploaded",
        "split": split,
        "filename": dest_file.name,
        "size_bytes": len(content),
    }


@app.get("/api/demo/eml/{filename}")
async def api_get_demo_eml(filename: str):
    allowed = {
        "demo_phishing.eml": "demo_phishing.eml",
        "demo_spam.eml": "demo_spam.eml",
        "demo_review.eml": "demo_review.eml",
    }
    if filename not in allowed:
        raise HTTPException(status_code=404, detail="Demo file not found")
    eml_path = Path(__file__).parents[2] / "data" / "demo_emls" / allowed[filename]
    if not eml_path.exists():
        raise HTTPException(status_code=404, detail="Demo file not found on server")
    return FileResponse(eml_path, media_type="message/rfc822", filename=filename)


@app.post("/api/retrain/run")
async def api_retrain_run(payload: dict):
    mode = payload.get("mode", "full")
    if mode not in ("full", "calibrate", "scratch"):
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'scratch', 'full', or 'calibrate'.")

    from scripts.retrain import execute_retrain
    try:
        result = execute_retrain(mode=mode, exit_on_fail=False)
        return result
    except Exception as e:
        return {"success": False, "message": f"Retraining failed with exception: {e}"}


@app.post("/api/model/promote")
async def api_model_promote(payload: dict):
    version = payload.get("version")
    if not version:
        raise HTTPException(status_code=400, detail="Missing required 'version' field.")

    from scripts.promote_model import promote_checkpoint
    res = promote_checkpoint(version)
    if res["success"]:
        reload_predictor()
    return res


@app.post("/api/model/reload")
async def api_model_reload():
    manifest = reload_predictor()
    return {"status": "ok", "version": manifest.get("version", "")}


@app.get("/api/model/phase3-status")
async def api_phase3_status():
    return get_phase3_status()


@app.get("/api/model/available")
async def api_available_models():
    global _predictor
    if _predictor is None:
        reload_predictor()
    return _predictor.available_models()


# ---------------------------------------------------------------------------
# System Health & Model Info
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", model_version=_predictor.version())


@app.get("/model/info", response_model=ModelInfoResponse)
@app.get("/api/model/info", response_model=ModelInfoResponse)
async def model_info():
    global _manifest
    if not _manifest:
        reload_predictor()
    return ModelInfoResponse(
        model_version=_manifest.get("version", "LightGBM"),
        model_type=_manifest.get("model_type", "lightgbm"),
        training_date=_manifest.get("training_date", ""),
        dataset_version=_manifest.get("dataset_version", ""),
        metrics=_manifest.get("metrics", {}),
    )


# ---------------------------------------------------------------------------
# Metrics (Prometheus text format)
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
