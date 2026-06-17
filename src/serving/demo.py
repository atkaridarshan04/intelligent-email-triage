"""
demo.py — Minimal demo UI served by FastAPI (Jinja2 templates).

Routes:
  GET  /demo/              → Triage page (upload / paste email)
  POST /demo/triage        → Runs triage, renders result card
  GET  /demo/queue         → Review queue (most uncertain first)
  GET  /demo/verdict/{id}  → Full triage result + verdict form
  POST /demo/verdict/{id}  → Submit analyst verdict, redirect to queue
"""
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

demo_router = APIRouter(prefix="/demo")


# ---------------------------------------------------------------------------
# Page 1 — Triage
# ---------------------------------------------------------------------------

@demo_router.get("/", response_class=HTMLResponse)
async def triage_page(request: Request):
    return templates.TemplateResponse("triage.html", {"request": request})


@demo_router.post("/triage", response_class=HTMLResponse)
async def run_triage(request: Request, email_text: str = Form("")):
    from src.serving.api import _predictor
    if _predictor is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    result = _predictor.triage_json({
        "subject": "",
        "body_text": email_text,
    })

    from src.feedback.store import FeedbackStore
    FeedbackStore().save_triage(result, body_text=email_text)

    return templates.TemplateResponse("triage.html", {
        "request": request,
        "result": {
            "email_id": result.email_id,
            "label": result.label,
            "predicted_class": result.predicted_class,
            "trust_score": result.trust_score,
            "spam_probability": result.spam_probability,
            "phishing_probability": result.phishing_probability,
            "routed_to_review": result.routed_to_review,
            "security_override": result.security_override,
            "reasons": result.reasons,
            "confidence_notes": result.confidence_notes,
            "model_version": result.model_version,
        },
        "email_text": email_text,
    })


# ---------------------------------------------------------------------------
# Page 2 — Review Queue
# ---------------------------------------------------------------------------

@demo_router.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request):
    from src.feedback.store import FeedbackStore
    rows = FeedbackStore().get_review_queue(limit=100)
    return templates.TemplateResponse("queue.html", {"request": request, "rows": rows})


# ---------------------------------------------------------------------------
# Page 3 — Verdict
# ---------------------------------------------------------------------------

@demo_router.get("/verdict/{email_id}", response_class=HTMLResponse)
async def verdict_page(request: Request, email_id: str):
    import json as _json
    from src.feedback.store import FeedbackStore
    store = FeedbackStore()
    with store._conn() as conn:
        row = conn.execute(
            "SELECT * FROM triage_log WHERE email_id = ?", (email_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Email not found")
    item = dict(row)
    item["reasons"] = _json.loads(item.get("reasons") or "[]")
    return templates.TemplateResponse("verdict.html", {"request": request, "item": item})


@demo_router.post("/verdict/{email_id}", response_class=HTMLResponse)
async def submit_verdict(
    request: Request,
    email_id: str,
    analyst_label: str = Form(...),
    notes: str = Form(""),
):
    from src.feedback.store import FeedbackStore
    updated = FeedbackStore().record_verdict(
        email_id=email_id,
        analyst_label=analyst_label,
        analyst_id="demo-analyst",
        notes=notes or None,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Email not found")
    return RedirectResponse(url="/demo/queue", status_code=303)
