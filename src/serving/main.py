"""
FastAPI application — email triage inference server.

Endpoints:
    POST /predict          — upload .eml → prediction JSON
    POST /feedback/{id}    — analyst submits verdict
    GET  /health           — liveness check
    GET  /                 — serves the web UI
"""
import hashlib
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.ingestion.email_parser import parse_eml
from src.inference.predictor import predict
from src.serving.schemas import FeedbackRequest, PredictionResponse
from src.serving.store import init_db, save_feedback, save_prediction

app = FastAPI(title="Email Triage API", version="1.0")

# Serve static UI files
_STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC), name="static")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def ui():
    return FileResponse(_STATIC / "index.html")


@app.post("/predict", response_model=PredictionResponse)
async def predict_email(file: UploadFile = File(...)):
    if not file.filename.endswith(".eml"):
        raise HTTPException(status_code=400, detail="Only .eml files accepted")

    raw = await file.read()
    eml_hash = hashlib.sha256(raw).hexdigest()
    features = parse_eml(raw)
    result   = predict(features)
    pred_id  = save_prediction(eml_hash, features, result)

    return {**result, "id": pred_id}


@app.post("/feedback/{pred_id}")
def feedback(pred_id: str, body: FeedbackRequest):
    valid = {"spam", "junk", "phishing", "safe"}
    if body.analyst_verdict not in valid:
        raise HTTPException(status_code=400, detail=f"verdict must be one of {valid}")
    if not save_feedback(pred_id, body.analyst_verdict):
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {"status": "ok"}
