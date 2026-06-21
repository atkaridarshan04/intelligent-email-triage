# Quickstart

This system triages user-reported suspicious emails as **Spam**, **Phishing**, or **Analyst Review**. It exposes a REST API and a demo UI. The only thing you need to provide is the trained model artifacts.

---

## Prerequisites

- Python 3.12+
- `pip install -r requirements.txt`
- (Optional) Docker for containerised deployment

---

## Step 1 — Add model artifacts

The system supports two models. Choose one (or both) to export.

### LightGBM (recommended — production model)

Download from your Kaggle Phase 2b notebook output:
- `lgbm_phase2.txt`
- `tfidf_phase2.pkl`
- `calibrated_phase2.pkl`

Then run:
```bash
python scripts/export_artifacts.py --model lightgbm --source /path/to/kaggle/outputs
```

This writes `lgbm.txt`, `tfidf.pkl`, and `calibration.json` into `checkpoints/production/`.

### Transformer (optional — Phase 3 experimental)

Download from your Kaggle Phase 3 notebook output:
- `roberta_hybrid_phase3.pt`
- `phase3_temperature.pkl`

Export into a versioned directory:
```bash
python scripts/export_artifacts.py --model transformer \
    --source /path/to/kaggle/outputs \
    --dest checkpoints/transformer-v1.0
```

---

## Step 2 — Start the API

```bash
uvicorn src.serving.api:app --reload
```

Verify it's running:
```bash
curl http://localhost:8000/health
# {"status": "ok", "model_version": "lightgbm-v1.0"}
```

---

## Step 3 — Triage an email

```bash
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Verify your account immediately",
    "body_text": "Click here to confirm your password.",
    "sender_address": "noreply@susp1c10us.xyz"
  }'
```

Response includes `label`, `trust_score`, `spam_prob`, `phishing_prob`, and `reasons[]`.

---

## Step 4 — Open the demo UI

```
http://localhost:8000/demo/
```

Three pages:
- **Triage** — paste an email, see the result
- **Review Queue** — emails awaiting analyst review, ordered by uncertainty
- **Verdict** — confirm or override the model's decision

---

## Run in Docker

```bash
docker-compose up
```

Volumes mount `data/` and `checkpoints/` so feedback persists and model promotions take effect without a rebuild.

---

## Switching models

The active model is controlled by `checkpoints/production/manifest.json`. To promote a different model:

```bash
python scripts/promote_model.py --version transformer-v1.0
```

Then restart the API. No code changes needed.

To switch back:
```bash
python scripts/promote_model.py --version lightgbm-v1.0
```

---

## After going live

| Task | Command |
|---|---|
| Retrain on analyst feedback | `python scripts/retrain.py --mode full` |
| Recalibrate only (< 500 new samples) | `python scripts/retrain.py --mode calibrate` |
| Promote a new model | `python scripts/promote_model.py --version MODEL-vX.Y` |
| Evaluate a checkpoint | `python scripts/evaluate_model.py --checkpoint checkpoints/MODEL-vX.Y` |

Retraining is gated: a new model only replaces production if phishing recall ≥ current production. No automatic promotion — you confirm every deployment.
