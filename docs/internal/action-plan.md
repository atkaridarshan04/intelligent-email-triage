# Action Plan — Making the System Operational

**Date:** 2026-06-21
**System status:** All code complete. 149 tests passing. Blocked only on model artifacts.

For a new user, start with `QUICKSTART.md`. This document has the full detail.

---

## Step 1 — Export LightGBM artifacts (blocking)

Download from Kaggle Phase 2b notebook output (`notebooks/pashe2b.ipynb`):

| File | What it is |
|---|---|
| `lgbm_phase2.txt` | Trained LightGBM booster |
| `tfidf_phase2.pkl` | Fitted TF-IDF vectorizer |
| `calibrated_phase2.pkl` | Calibrated model wrapper (Platt params extracted from this) |

```bash
python scripts/export_artifacts.py --model lightgbm --source /path/to/kaggle/outputs
```

Writes into `checkpoints/production/`: `lgbm.txt`, `tfidf.pkl`, `calibration.json`.

If the export script warns it couldn't extract Platt params (`a=1.0, b=0.0` in `calibration.json`), refit calibration:
```bash
python scripts/retrain.py --mode calibrate
```

---

## Step 2 — (Optional) Export transformer artifacts

Download from Kaggle Phase 3 notebook output (`notebooks/phase3_transformer.py`):

| File | What it is |
|---|---|
| `roberta_hybrid_phase3.pt` | RoBERTa+MLP model weights |
| `phase3_temperature.pkl` | Temperature scaling factor |

```bash
python scripts/export_artifacts.py --model transformer \
    --source /path/to/kaggle/outputs \
    --dest checkpoints/transformer-v1.0
```

Add a `manifest.json` to `checkpoints/transformer-v1.0/` with `"model_type": "transformer"` then promote:
```bash
python scripts/promote_model.py --version transformer-v1.0
```

---

## Step 3 — Verify the API starts

```bash
uvicorn src.serving.api:app --reload
curl http://localhost:8000/health
# {"status": "ok", "model_version": "lightgbm-v1.0"}
```

If startup fails it will name the missing artifact.

---

## Step 4 — Smoke test

```bash
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"subject": "Verify your account", "body_text": "Click here to confirm your password.", "sender_address": "noreply@susp1c10us.xyz"}'
```

Expect a `TriageResponse` with `label`, `trust_score`, `spam_prob`, `phishing_prob`, `reasons[]`.

---

## Step 5 — Run the demo UI

```
http://localhost:8000/demo/
```

Three pages: Triage → Review Queue → Verdict.

---

## Step 6 (optional) — Docker

```bash
docker-compose up
```

`data/` and `checkpoints/` are volume-mounted — feedback persists and model promotions take effect without a rebuild.

---

## Switching models

The active model is driven entirely by `checkpoints/production/manifest.json`. No code changes needed.

```bash
# Switch to transformer
python scripts/promote_model.py --version transformer-v1.0

# Switch back to LightGBM
python scripts/promote_model.py --version lightgbm-v1.0
```

Restart the API after promoting.

---

## Ongoing operations

| Task | Command |
|---|---|
| Retrain on analyst feedback | `python scripts/retrain.py --mode full` |
| Recalibrate only | `python scripts/retrain.py --mode calibrate` |
| Promote a model | `python scripts/promote_model.py --version MODEL-vX.Y` |

Retraining is gated: new model only promotes if phishing recall ≥ production. No automatic promotion.
