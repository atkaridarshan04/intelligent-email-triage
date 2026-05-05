# Serving Layer

FastAPI server that wraps the trained model and exposes it as an HTTP API.

## Architecture

```
.eml upload
    │
    ▼
email_parser.py        — parse raw bytes → feature dict (14 fields)
    │
    ▼
predictor.py           — feature dict → model forward pass → routing logic
    │
    ▼
store.py               — persist prediction to SQLite (data/predictions.db)
    │
    ▼
JSON response          — label, trust_score, risk_score, class_probabilities,
                         active_signals, monitoring_flag, id
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Web UI (static/index.html) |
| `GET` | `/health` | Liveness check |
| `POST` | `/predict` | Upload `.eml` → prediction JSON |
| `POST` | `/feedback/{id}` | Submit analyst verdict for a prediction |

### POST /predict

**Request:** `multipart/form-data` with a single field `file` containing a `.eml` file.

**Response:**
```json
{
  "id": "uuid",
  "label": "Phishing",
  "trust_score": 91.4,
  "risk_score": 87,
  "class_probabilities": {
    "spam": 0.012,
    "junk": 0.003,
    "phishing": 0.985
  },
  "active_signals": ["spf_fail_dkim_fail", "reply_to_mismatch"],
  "monitoring_flag": false
}
```

**Labels:** `Spam` | `Junk` | `Phishing` | `Analyst Review`

`monitoring_flag: true` means the prediction was auto-routed but with trust between 55–75 — worth a spot check.

### POST /feedback/{id}

**Request body:**
```json
{ "analyst_verdict": "phishing" }
```

Valid verdicts: `spam`, `junk`, `phishing`, `safe`.

Stores the analyst verdict against the prediction in SQLite for use in future retraining.

## Routing Logic

| Condition | Label |
|---|---|
| `phishing_prob ≥ 0.70` AND active high-weight signals present | `Phishing` (override) |
| `trust > 55` | Top predicted class |
| `trust ≤ 55` | `Analyst Review` |

Trust score = `0.6 × max_prob + 0.4 × (max_prob − second_prob)` × 100

Risk score = `(phishing_prob × 0.7 + junk_prob × 0.2 + spam_prob × 0.1)` × 100

## Running Locally

### With Docker (recommended)

```bash
docker build -t email-triage .
docker run -p 8000:8000 email-triage
```

Open `http://localhost:8000` for the web UI, or use the API directly.

### Without Docker

```bash
pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
uvicorn src.serving.main:app --reload
```

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Predict
curl -X POST http://localhost:8000/predict \
  -F "file=@security_alert.eml"

# Submit feedback
curl -X POST http://localhost:8000/feedback/<id> \
  -H "Content-Type: application/json" \
  -d '{"analyst_verdict": "phishing"}'
```

Test `.eml` files: the SpamAssassin public corpus at
`https://spamassassin.apache.org/old/publiccorpus/` has hundreds of labeled spam
and ham samples. Download any tarball, rename a file to `.eml`, and upload.

## Persistence

All predictions are stored in `data/predictions.db` (SQLite). Schema:

| Column | Description |
|---|---|
| `id` | UUID, used for feedback linkage |
| `timestamp` | UTC ISO-8601 |
| `eml_hash` | SHA-256 of raw bytes (dedup signal) |
| `predicted_label` | Routing outcome |
| `spam_prob / junk_prob / phishing_prob` | Raw model outputs |
| `trust_score / risk_score` | Derived scores |
| `active_signals` | Comma-separated signal names |
| `analyst_verdict` | Filled by `/feedback` endpoint |
| `feedback_at` | UTC timestamp of feedback |

## Module Responsibilities

| File | Role |
|---|---|
| `src/serving/main.py` | FastAPI app, route handlers |
| `src/serving/schemas.py` | Pydantic request/response models |
| `src/serving/store.py` | SQLite read/write |
| `src/ingestion/email_parser.py` | `.eml` → feature dict |
| `src/inference/predictor.py` | Feature dict → prediction |
| `src/models/model.py` | `EmailTriageModel` definition |
| `src/utils/tld_lookup.py` | TLD risk score lookup |
