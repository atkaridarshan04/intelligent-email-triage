# Model Serving — Implementation Results

Record of decisions, architecture choices, and known limitations for the serving layer.

## Model Artifact

- **Source:** Kaggle notebook `spam-phishing.ipynb`, trained on GPU (Tesla T4)
- **Architecture:** RoBERTa-base + metadata MLP fusion → 3-class classifier
- **Checkpoint format:** PyTorch sharded directory (`outputs/best/`)
- **Loaded via:** `torch.load("outputs/best", map_location=device, weights_only=True)`
- **Test set performance (3-class):**

| Class | Precision | Recall | F1 |
|---|---|---|---|
| Spam | 1.00 | 0.99 | 0.99 |
| Junk | 1.00 | 1.00 | 1.00 |
| Phishing | 0.99 | 1.00 | 0.99 |
| **Overall accuracy** | | **99.47%** | |

## Model Architecture

```
Input text (subject + sender + url_token_text + body)
    │
    ▼
RoBERTa-base encoder → mean pooling → 768-dim
    │
    ├── concat ──────────────────────────────────┐
    │                                            │
Input metadata (10 features)                    │
    │                                            │
    ▼                                            │
Linear(10→64) → ReLU → LayerNorm → Dropout(0.3) ┘
    │
    ▼
Linear(832→3) → logits → softmax → class probs
```

**Metadata features (in order):**
1. `spf_result` — pass=1.0, softfail=0.5, fail=0.0, none=−1.0
2. `dkim_result` — pass=1.0, fail=0.0, none=−1.0
3. `dmarc_result` — pass=1.0, fail=0.0, none=−1.0
4. `url_count`
5. `attachment_count`
6. `reply_to_mismatch` — 0.0 / 1.0
7. `html_text_ratio`
8. `tld_risk_score` — 1 (low) / 2 (medium) / 3 (high)
9. `sender_seen_before` — 0.0 / 1.0
10. `first_time_domain` — 0.0 / 1.0

## Serving Decisions

**Analyst Review is not a model class.** The model outputs 3 classes (spam/junk/phishing). `Analyst Review` is a runtime routing state triggered when trust ≤ 55. This keeps training labels clean and confidence calibration reliable.

**Model loaded as singleton.** `_load_model()` in `predictor.py` loads once on first request and caches globally. Avoids reloading 500MB on every call.

**RoBERTa downloaded at Docker build time.** Added a `RUN python -c "...from_pretrained('roberta-base')..."` step in the Dockerfile so the model weights are baked into the image. Without this, the first request triggers a ~500MB download and times out.

**CPU-only inference.** The Docker image uses `torch --index-url https://download.pytorch.org/whl/cpu` to avoid pulling the 2.5GB CUDA wheel. Inference on CPU is acceptable for this use case (single-email, non-batch).

**SQLite for persistence.** Predictions and analyst feedback are stored in `data/predictions.db`. Chosen for zero-dependency simplicity. For production, replace with Postgres.

## Known Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| No request batching | Each `.eml` runs a separate forward pass | Acceptable for analyst-driven triage volume |
| `sender_seen_before` / `first_time_domain` always use parser defaults | Behavioral history not wired to a live store | Future: query `predictions.db` sender history |
| No auth on API endpoints | Any client can submit predictions or feedback | Add API key middleware before production deployment |
| SQLite not safe for concurrent writes | Race condition under parallel requests | Use `check_same_thread=False` + connection pool, or switch to Postgres |
| Model not versioned in artifact path | Retraining overwrites `outputs/best/` | Tag artifacts by run ID before deploying retrained models |

## Files Changed During Implementation

| File | Change |
|---|---|
| `src/serving/main.py` | FastAPI app with lifespan, `/predict`, `/feedback`, `/health`, static UI |
| `src/serving/schemas.py` | `PredictionResponse` (with `id`), `FeedbackRequest` |
| `src/serving/store.py` | SQLite init, `save_prediction`, `save_feedback` |
| `src/inference/predictor.py` | Full inference pipeline wrapping `EmailTriageModel` |
| `src/models/model.py` | `EmailTriageModel` matching notebook architecture |
| `requirements.txt` | Added `torch`, `transformers`, `pydantic`, `numpy` |
| `Dockerfile` | CPU-only torch, roberta-base pre-download layer |
| `.dockerignore` | Exclude training data, keep `data/tld_risk_scores.json` |
