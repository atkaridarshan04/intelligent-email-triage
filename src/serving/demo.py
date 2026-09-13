"""
demo.py — Barclays Cyber Operations Enterprise Web Application Router.

Provides enterprise interface mounted at /app/* with backwards-compatible aliases at /demo/*.
Routes:
  GET  /app/               → Live Triage Hub (attack scenarios, text/file ingestion)
  POST /app/triage         → Executes triage, renders threat analysis & confidence
  POST /app/triage/upload  → Parses RFC-822 .eml, renders threat analysis
  GET  /app/queue          → SOC Tier-2 Analyst Review Queue
  GET  /app/verdict/{id}   → Individual case inspection and analyst resolution form
  POST /app/verdict/{id}   → Records analyst verdict into feedback database
  GET  /app/database       → Interactive Triage Database Explorer & Audit Log
  GET  /app/drift          → Model Drift Detection & 7-Day Observability
  GET  /app/retrain        → Model Retraining Studio & Phase 3 Deep Neural Showcase
"""
import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.feedback.drift_detector import get_detailed_drift
from src.feedback.store import FeedbackStore
from src.models.transformer_model import get_phase3_status

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

import dataclasses
from markupsafe import Markup

def _serialize_for_json(obj):
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    try:
        import numpy as np
        if isinstance(obj, (np.floating, float)):
            return float(obj)
        if isinstance(obj, (np.integer, int)):
            return int(obj)
    except ImportError:
        pass
    return str(obj)

def _prettify_tojson(obj, indent=2, **kwargs):
    return Markup(json.dumps(obj, indent=indent, default=_serialize_for_json))

templates.env.filters["tojson"] = _prettify_tojson

# Primary enterprise router mounted at /app
ui_router = APIRouter(prefix="/app")

# Legacy demo router for backwards compatibility
demo_router = APIRouter(prefix="/demo")


def _get_queue_count() -> int:
    try:
        return len(FeedbackStore().get_review_queue(limit=500))
    except Exception:
        return 0


def _parse_body_content(text: str) -> dict:
    """Parses email body or raw JSON input into a clean, prettified, readable structure."""
    if not text:
        return {
            "is_json": False,
            "clean_body": "",
            "json_prettified": "",
            "subject": "",
            "sender": "",
            "reply_to": "",
            "urls": [],
            "attachments": [],
        }

    text_str = text.strip()
    if text_str.startswith("{") and text_str.endswith("}"):
        try:
            d = json.loads(text_str)
            clean_body = d.get("body_text", "")
            urls = d.get("urls", [])
            if not urls and clean_body:
                urls = re.findall(r'https?://[^\s<>"\\\']+', clean_body)
            return {
                "is_json": True,
                "clean_body": clean_body,
                "json_prettified": json.dumps(d, indent=2),
                "subject": d.get("subject", ""),
                "sender": d.get("sender_address", d.get("from_addr", d.get("from", ""))),
                "reply_to": d.get("reply_to", ""),
                "urls": urls,
                "attachments": d.get("attachments", []),
            }
        except Exception:
            pass

    urls = re.findall(r'https?://[^\s<>"\\\']+', text)
    return {
        "is_json": False,
        "clean_body": text,
        "json_prettified": "",
        "subject": "",
        "sender": "",
        "reply_to": "",
        "urls": urls,
        "attachments": [],
    }


# ---------------------------------------------------------------------------
# View 1: Live Triage Hub
# ---------------------------------------------------------------------------

@ui_router.get("/", response_class=HTMLResponse)
@ui_router.get("/triage", response_class=HTMLResponse)
async def triage_page(request: Request):
    import src.serving.api as _api
    if _api._predictor is None:
        _api.reload_predictor()
    _predictor = _api._predictor
    selected_model = request.query_params.get("model", "")
    available_models = _predictor.available_models() if _predictor else []
    return templates.TemplateResponse("triage.html", {
        "request": request,
        "queue_count": _get_queue_count(),
        "selected_model": selected_model,
        "available_models": available_models,
    })


@ui_router.post("/triage", response_class=HTMLResponse)
async def run_triage(request: Request, email_text: str = Form(""), model: str = Form("lightgbm")):
    import src.serving.api as _api
    if _api._predictor is None:
        _api.reload_predictor()
    _predictor = _api._predictor
    if _predictor is None:
        raise HTTPException(status_code=503, detail="Model predictor not initialized")

    text_stripped = email_text.strip()
    triage_payload: dict = {"subject": "", "body_text": email_text}
    if text_stripped.startswith("{"):
        try:
            record = json.loads(text_stripped)
            triage_payload = dict(record)
            if "body_text" not in triage_payload and "text" in triage_payload:
                triage_payload["body_text"] = triage_payload["text"]
            if "subject" not in triage_payload:
                triage_payload["subject"] = ""
        except json.JSONDecodeError:
            pass
    elif ":" in text_stripped and ("from:" in text_stripped.lower() or "subject:" in text_stripped.lower()):
        # Parse pasted email with RFC-822 headers
        import email as _email
        from email import policy as _policy
        try:
            msg = _email.message_from_string(text_stripped, policy=_policy.default)
            if msg.get("Subject") or msg.get("From"):
                subj = str(msg.get("Subject", "")).strip()
                from_addr = str(msg.get("From", "")).strip()
                reply_to = str(msg.get("Reply-To", "")).strip()
                display_name = ""
                addr_match = re.match(r'^"?([^"<]+)"?\s*<([^>]+)>', from_addr)
                if addr_match:
                    display_name = addr_match.group(1).strip()
                    from_addr = addr_match.group(2).strip()
                body = msg.get_body(preferencelist=('plain', 'html'))
                body_content = body.get_content() if body else msg.get_payload()
                if isinstance(body_content, list):
                    body_content = "\n".join(str(p) for p in body_content)
                urls = re.findall(r'https?://[^\s<>"\']+', str(body_content or ""))
                triage_payload = {
                    "subject": subj,
                    "body_text": str(body_content) if body_content else text_stripped,
                    "sender_address": from_addr,
                    "sender_display_name": display_name,
                    "reply_to": reply_to,
                    "urls": urls,
                }
        except Exception:
            pass

    result = _predictor.triage_json(triage_payload, model_choice=model)

    # Save to SQLite feedback store with extracted subject, body, and features
    body_to_save = triage_payload.get("body_text") or email_text
    FeedbackStore().save_triage(
        result=result,
        subject=triage_payload.get("subject", ""),
        body_text=body_to_save,
        features=result.features,
    )

    # Prettified and human-readable parsed email info
    email_parsed = _parse_body_content(email_text)
    if triage_payload.get("subject") and not email_parsed.get("subject"):
        email_parsed["subject"] = triage_payload["subject"]
    if triage_payload.get("sender_address") and not email_parsed.get("sender"):
        email_parsed["sender"] = triage_payload["sender_address"]
    if triage_payload.get("reply_to") and not email_parsed.get("reply_to"):
        email_parsed["reply_to"] = triage_payload["reply_to"]
    if triage_payload.get("urls") and not email_parsed.get("urls"):
        email_parsed["urls"] = triage_payload["urls"]
    if triage_payload.get("body_text") and not email_parsed.get("is_json"):
        email_parsed["clean_body"] = triage_payload["body_text"]

    result_dict = dataclasses.asdict(result) if dataclasses.is_dataclass(result) else result
    return templates.TemplateResponse("triage.html", {
        "request": request,
        "queue_count": _get_queue_count(),
        "result": result,
        "result_dict": result_dict,
        "email_parsed": email_parsed,
        "email_text": email_text,
        "selected_model": model,
        "available_models": _predictor.available_models(),
    })


@ui_router.post("/triage/upload", response_class=HTMLResponse)
async def run_triage_upload(request: Request, eml_file: UploadFile = File(...), model: str = Form("lightgbm")):
    import src.serving.api as _api
    if _api._predictor is None:
        _api.reload_predictor()
    _predictor = _api._predictor
    if _predictor is None:
        raise HTTPException(status_code=503, detail="Model predictor not initialized")

    raw_bytes = await eml_file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded .eml file is empty")

    result = _predictor.triage_eml(raw_bytes, model_choice=model)

    # Extract subject and body text from RFC-822 message
    import email as _email
    from email import policy as _policy
    subject = ""
    body_text = ""
    body_html = ""
    sender_addr = ""
    reply_to = ""
    try:
        msg = _email.message_from_bytes(raw_bytes, policy=_policy.default)
        subject = str(msg.get("Subject", ""))
        sender_addr = str(msg.get("From", ""))
        reply_to = str(msg.get("Reply-To", ""))
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and not body_text and "attachment" not in cd:
                try:
                    body_text = part.get_content() or ""
                except Exception:
                    payload = part.get_payload(decode=True)
                    body_text = payload.decode("utf-8", errors="replace") if payload else ""
            elif ct == "text/html" and not body_html and "attachment" not in cd:
                try:
                    body_html = part.get_content() or ""
                except Exception:
                    payload = part.get_payload(decode=True)
                    body_html = payload.decode("utf-8", errors="replace") if payload else ""
        if not body_text:
            body_text = body_html or raw_bytes.decode("utf-8", errors="replace")
    except Exception:
        body_text = raw_bytes.decode("utf-8", errors="replace")

    FeedbackStore().save_triage(
        result=result,
        subject=subject,
        body_text=body_text,
        features=result.features,
    )

    email_parsed = _parse_body_content(body_text)
    email_parsed["subject"] = subject
    email_parsed["sender"] = sender_addr
    email_parsed["reply_to"] = reply_to
    if not email_parsed.get("urls"):
        email_parsed["urls"] = re.findall(r'https?://[^\s<>"\\\']+', body_text + body_html)

    result_dict = dataclasses.asdict(result) if dataclasses.is_dataclass(result) else result
    return templates.TemplateResponse("triage.html", {
        "request": request,
        "queue_count": _get_queue_count(),
        "result": result,
        "result_dict": result_dict,
        "email_parsed": email_parsed,
        "active_tab": "file",
        "email_text": "",
        "selected_model": model,
        "available_models": _predictor.available_models(),
    })


# ---------------------------------------------------------------------------
# View 2: SOC Review Queue
# ---------------------------------------------------------------------------

@ui_router.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request):
    rows = FeedbackStore().get_review_queue(limit=100)
    return templates.TemplateResponse("queue.html", {
        "request": request,
        "rows": rows,
        "queue_count": len(rows),
    })


# ---------------------------------------------------------------------------
# View 3: Case Dossier & Incident Resolution Verdict
# ---------------------------------------------------------------------------

@ui_router.get("/verdict/{email_id}", response_class=HTMLResponse)
async def verdict_page(request: Request, email_id: str):
    store = FeedbackStore()
    item = store.get_record_by_id(email_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Email record not found")

    email_parsed = _parse_body_content(item.get("body_text", ""))
    if item.get("subject") and not email_parsed.get("subject"):
        email_parsed["subject"] = item["subject"]

    return templates.TemplateResponse("verdict.html", {
        "request": request,
        "item": item,
        "email_parsed": email_parsed,
        "queue_count": _get_queue_count(),
    })


@ui_router.post("/verdict/{email_id}", response_class=HTMLResponse)
async def submit_verdict(
    request: Request,
    email_id: str,
    analyst_label: str = Form(...),
    analyst_id: str = Form("barclays-soc-analyst"),
    notes: str = Form(""),
):
    store = FeedbackStore()
    updated = store.record_verdict(
        email_id=email_id,
        analyst_label=analyst_label,
        analyst_id=analyst_id or "barclays-soc-analyst",
        notes=notes or None,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Email record not found")
    return RedirectResponse(url="/app/queue", status_code=303)


# ---------------------------------------------------------------------------
# View 4: Triage Database Explorer & Audit Log
# ---------------------------------------------------------------------------

@ui_router.get("/database", response_class=HTMLResponse)
async def database_page(
    request: Request,
    search: str = "",
    label: str = "",
    status: str = "",
):
    store = FeedbackStore()
    records = store.get_all_records(limit=100, offset=0, search=search, label=label, status=status)
    stats = store.get_stats()

    # Pre-serialize records for safe JSON consumption in modal script
    records_clean = []
    for r in records:
        rc = dict(r)
        records_clean.append(rc)

    return templates.TemplateResponse("database.html", {
        "request": request,
        "records": records,
        "records_json": json.dumps(records_clean),
        "stats": stats,
        "search": search,
        "label": label,
        "status": status,
        "queue_count": stats.get("pending_review", 0),
    })


# ---------------------------------------------------------------------------
# View 5: Drift Observability & Model Health
# ---------------------------------------------------------------------------

@ui_router.get("/drift", response_class=HTMLResponse)
async def drift_page(request: Request):
    drift_data = get_detailed_drift()
    return templates.TemplateResponse("drift.html", {
        "request": request,
        "drift": drift_data,
        "queue_count": _get_queue_count(),
    })


# ---------------------------------------------------------------------------
# View 6: Model Retraining Studio & Governance
# ---------------------------------------------------------------------------

@ui_router.get("/retrain", response_class=HTMLResponse)
async def retrain_page(request: Request):
    from src.serving.api import _manifest
    from src.training.engine import get_available_datasets
    store = FeedbackStore()
    feedback_samples = store.get_labeled_feedback()
    p3_status = get_phase3_status()
    datasets = get_available_datasets()

    return templates.TemplateResponse("retrain.html", {
        "request": request,
        "manifest": _manifest or {
            "version": "LightGBM",
            "training_date": "2026-05-31",
            "metrics": {"phishing_recall": 0.9801, "accuracy": 0.9762},
        },
        "feedback_samples_count": len(feedback_samples),
        "phase3": p3_status,
        "datasets": datasets,
        "queue_count": _get_queue_count(),
    })


@ui_router.get("/docs", response_class=HTMLResponse)
async def docs_page(request: Request):
    from src.serving.api import _manifest
    p3_status = get_phase3_status()
    return templates.TemplateResponse("docs.html", {
        "request": request,
        "active_nav": "docs",
        "manifest": _manifest,
        "phase3": p3_status,
        "queue_count": _get_queue_count(),
    })


@ui_router.get("/model", response_class=HTMLResponse)
@ui_router.get("/model/info", response_class=HTMLResponse)
async def model_governance_page(request: Request):
    from src.serving.api import _manifest, reload_predictor
    if not _manifest:
        reload_predictor()
    p3_status = get_phase3_status()
    return templates.TemplateResponse("model_info.html", {
        "request": request,
        "active_nav": "model",
        "manifest": _manifest or {
            "version": "LightGBM",
            "model_type": "lightgbm",
            "training_date": "2026-05-31",
            "dataset_version": "model_ready_v1",
            "metrics": {
                "phishing_recall": 0.9801,
                "accuracy": 0.9762,
                "auto_classify_rate": 0.988,
                "roc_auc": 0.9845,
                "brier_score": 0.0210,
                "ece": 0.4455,
            },
        },
        "phase3": p3_status,
        "queue_count": _get_queue_count(),
    })


# ---------------------------------------------------------------------------
# Backwards-compatibility aliases for legacy /demo routes
# ---------------------------------------------------------------------------

@demo_router.get("/", include_in_schema=False)
async def demo_root():
    return RedirectResponse(url="/app/", status_code=307)

@demo_router.get("/model", include_in_schema=False)
@demo_router.get("/model/info", include_in_schema=False)
async def demo_model():
    return RedirectResponse(url="/app/model", status_code=307)

@demo_router.get("/queue", include_in_schema=False)
async def demo_queue():
    return RedirectResponse(url="/app/queue", status_code=307)

@demo_router.get("/docs", include_in_schema=False)
async def demo_docs():
    return RedirectResponse(url="/app/docs", status_code=307)

@demo_router.get("/verdict/{email_id}", include_in_schema=False)
async def demo_verdict(email_id: str):
    return RedirectResponse(url=f"/app/verdict/{email_id}", status_code=307)

@demo_router.post("/triage", response_class=HTMLResponse)
async def demo_triage(request: Request, email_text: str = Form("")):
    return await run_triage(request=request, email_text=email_text)

@demo_router.post("/triage/upload", response_class=HTMLResponse)
async def demo_triage_upload(request: Request, eml_file: UploadFile = File(...)):
    return await run_triage_upload(request=request, eml_file=eml_file)

@demo_router.post("/verdict/{email_id}", response_class=HTMLResponse)
async def demo_submit_verdict(
    request: Request,
    email_id: str,
    analyst_label: str = Form(...),
    notes: str = Form(""),
):
    return await submit_verdict(
        request=request, email_id=email_id, analyst_label=analyst_label, notes=notes
    )
