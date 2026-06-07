# Engineering System Design

**Date:** 2026-06-07
**Status:** Decided — pre-implementation

---

## Guiding Principles

- The system is model-agnostic. LightGBM is the current production artifact; the transformer
  is the intended long-term artifact. Neither decision belongs in the system design.
- The model is a plugin. The inference engine, feedback store, retraining pipeline, and API
  are all designed independently of what sits behind the `predict()` call.
- The full feature set is always extracted. We eliminated features during training due to
  our own dataset limitations — not because those features are uninformative. On client data
  all structured features are available and all are passed to the model. The feature pipeline
  does not make assumptions about which features matter.
- Retraining is a first-class operation. The system is only valuable if it improves over
  time. Analyst-reviewed emails are the most valuable data asset — they are stored durably,
  exportable, and feed directly into the retrain pipeline.
- Client data stays on client infrastructure. The system ships as a portable Docker container
  with a self-contained retraining workflow.
- Every component has one responsibility and one interface. No component depends on model
  internals.

---

## System Overview

```
Reported Email (raw .eml or JSON)
        │
        ▼
┌───────────────────┐
│   Email Parser    │  Extracts: subject, body_text, from, reply_to,
│  (src/parsing/)   │  headers, URLs, attachments
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Feature Extractor │  Produces: full structured feature vector
│ (src/features/)   │  (all features, no prior elimination)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Model Adapter    │  Calls model.predict(email_text, features)
│  (src/inference/  │  Returns: spam_prob, phishing_prob, attributions
│   predictor.py)   │  The only place that knows what model is loaded.
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Confidence Router │  trust_score → routing decision
│ (threshold_router)│  security override check
└────────┬──────────┘
         │
    ┌────┴──────────────┐──────────────────┐
    ▼                   ▼                  ▼
Auto: Spam        Auto: Phishing     Analyst Review
(suppress)        (escalate)         (review queue)
                                           │
                               ┌───────────▼───────────┐
                               │   POST /feedback       │
                               │   (analyst verdict)    │
                               └───────────┬───────────┘
                                           │
                               ┌───────────▼───────────┐
                               │    Feedback Store      │
                               │  (SQLite → Postgres)   │
                               └───────────┬───────────┘
                                           │
                               ┌───────────▼───────────┐
                               │  Retraining Pipeline   │
                               │  scripts/retrain.py    │
                               └───────────────────────┘
```

---

## The Model Adapter Contract

This is the central design decision. Every other component talks to the model through one
interface. The system never calls model internals directly.

```python
class ModelAdapter(Protocol):
    def predict(self, text: str, features: dict[str, float]) -> ModelOutput:
        """
        text     — concatenated subject + body (raw, untruncated)
        features — full structured feature dict, all fields present
        returns  — ModelOutput(spam_prob, phishing_prob, feature_attributions)
        """
        ...

    @property
    def version(self) -> str: ...

    @property
    def model_type(self) -> str: ...  # "lightgbm" | "transformer"
```

```python
@dataclass
class ModelOutput:
    spam_prob: float
    phishing_prob: float
    feature_attributions: dict[str, float]  # SHAP or IG scores, keyed by feature name
```

Two concrete adapters ship with the system:

**`LightGBMAdapter`** — loads `model.txt` + `vectorizer.pkl`, runs TF-IDF → LightGBM,
returns SHAP values as attributions.

**`TransformerAdapter`** — loads PyTorch checkpoint, runs tokenisation + structured MLP +
fusion, returns SHAP on structured features inline and dispatches Integrated Gradients as
a background task.

The API, confidence router, feedback store, and retrain pipeline never import either
adapter directly. They depend only on the `ModelAdapter` protocol. Swapping the production
model is a config change, not a code change.

---

## Components

### 1. REST API (`src/serving/api.py`)

FastAPI. Model-agnostic — calls the adapter, nothing else.

```
POST /triage
  body: { raw_email: string } | { subject, body_text, from_addr, reply_to, ... }
  response: TriageResponse

POST /feedback
  body: { email_id, analyst_label, analyst_id, notes }

GET  /feedback/queue          → pending analyst review items
GET  /health
GET  /model/info              → version, type, training date, metrics summary
GET  /metrics                 → Prometheus-format operational metrics
```

No auth — client infrastructure concern (mTLS, API key, OAuth). The API sits behind
whatever gateway the client runs.

---

### 2. Inference Engine (`src/inference/`)

**`predictor.py`**

Loads the active adapter at startup from `checkpoints/production/`. Runs the full pipeline:
parse → extract features → adapter.predict() → router → postprocess.

Adapter type is read from `checkpoints/production/manifest.json`. The predictor does not
know or care what type it is — it calls `adapter.predict()`.

Temperature scalar `T` and routing thresholds are loaded from config at startup, not
per-request.

Inference is synchronous. A transformer forward pass at ~100–200ms fits within the 300ms
budget. If the transformer's Tier 2 attribution (Integrated Gradients) is enabled, it is
dispatched as a FastAPI background task after the routing response is returned — it never
blocks the triage response.

**`threshold_router.py`** — stateless. Takes `(spam_prob, phishing_prob, T)`, returns
`RoutingDecision`. No model knowledge.

**`postprocess.py`** — builds `TriageResponse` from `ModelOutput` + `RoutingDecision`.
Feeds attributions to the rule summariser for human-readable reasons.

---

### 3. Feature Pipeline (`src/features/`)

Extracts the full structured feature set from every email, unconditionally. The pipeline
does not gate on feature variance, availability, or model type. All features are always
computed and always passed to the adapter. It is the adapter's responsibility to use or
ignore features as appropriate.

Feature groups:
- **Sender:** display/from mismatch, reply-to mismatch, free-email sender, sender domain age
- **URLs:** count, domain count, shortened URL, suspicious TLD, IP literal, entropy,
  typosquatting score, HTTPS ratio
- **Attachments:** presence, type (archive / executable / document), macro-enabled flag
- **Text statistics:** subject length, body length, uppercase ratio, digit ratio,
  punctuation density, link density
- **Brand:** known brand mention, sender-brand mismatch

Missing values (e.g. no attachment → attachment features are 0/False) are resolved in the
extractor. The adapter always receives a fully populated feature dict.

---

### 4. Feedback Store (`src/feedback/`)

The most important component for long-term value. Stores every analyst verdict durably with
the full feature snapshot, full text snapshot, and model's original prediction.

**Storage:** SQLite for v1. Zero infrastructure dependency, portable, client-inspectable.
Schema is identical to Postgres — migration is a one-liner when volume demands it.

**Schema:**

```sql
CREATE TABLE feedback (
    id               TEXT PRIMARY KEY,   -- UUID
    email_id         TEXT NOT NULL,      -- SHA-256 of raw email content
    received_at      TEXT NOT NULL,      -- ISO 8601
    model_version    TEXT NOT NULL,      -- from manifest.json

    -- Text snapshot — needed for transformer retraining
    subject          TEXT,
    body_text        TEXT,               -- plain text, HTML stripped

    -- Full feature snapshot — needed for LightGBM retraining and all evaluation
    features         TEXT NOT NULL,      -- JSON, all fields present, no nulls

    -- Model prediction at time of triage
    predicted_label  TEXT NOT NULL,      -- Spam | Phishing | Analyst Review
    spam_prob        REAL NOT NULL,
    phishing_prob    REAL NOT NULL,
    trust_score      REAL NOT NULL,

    -- Analyst verdict
    analyst_label    TEXT,               -- Spam | Phishing | Escalate | Defer | NULL
    analyst_id       TEXT,
    reviewed_at      TEXT,
    notes            TEXT,

    -- Derived
    agreement        INTEGER             -- 1 | 0 | NULL
);

CREATE INDEX idx_feedback_analyst_label ON feedback(analyst_label);
CREATE INDEX idx_feedback_reviewed_at   ON feedback(reviewed_at);
CREATE INDEX idx_feedback_model_version ON feedback(model_version);
CREATE INDEX idx_feedback_agreement     ON feedback(agreement);
```

Both `body_text` and `features` are stored. The transformer retraining needs raw text.
LightGBM retraining needs features. The feedback store supports either model family without
schema changes.

**`feedback_ingest.py`** — writes analyst verdicts. Called by `POST /feedback`.

**`drift_detector.py`** — monitors override rate (rolling 7-day window). Logs a retrain
trigger when override rate exceeds 20%. Does not trigger retraining automatically — a human
makes that call. Fully automated retraining without oversight is not appropriate for a
security system.

---

### 5. Retraining Pipeline (`scripts/retrain.py`)

**Design goal:** `python scripts/retrain.py` produces a validated new model from current
data + feedback. No notebooks, no manual steps, no external services.

The pipeline is model-aware only at the training step. Data loading, merging, evaluation,
gating, and artifact saving are all model-agnostic.

```
retrain.py
│
├── 1. Load base training data      data/model_ready/ (train + val + test splits)
│
├── 2. Load analyst feedback        feedback.db WHERE analyst_label IS NOT NULL
│      Export snapshot              data/feedback/exports/YYYYMMDD.jsonl
│
├── 3. Merge                        feedback labels take precedence over base labels
│                                   for matching email_id; new emails appended to train
│
├── 4. Train                        model type read from configs/train.yaml
│      LightGBM:                    refit TF-IDF on combined corpus + train LightGBM
│      Transformer:                 fine-tune from previous checkpoint, not from scratch
│
├── 5. Calibrate                    fit temperature scalar T on val set
│
├── 6. Evaluate                     src/training/evaluate.py on held-out test set
│
├── 7. Gate                         new phishing recall ≥ current production phishing recall
│      FAIL → abort, log warning, production model unchanged
│      PASS → continue
│
├── 8. Save artifacts               checkpoints/MODEL_TYPE-vX.Y/
│                                   manifest.json, temperature.json, model artifacts
│
└── 9. Report                       metrics comparison: production vs new model
                                    stdout + artifacts/reports/retrain-YYYYMMDD.md
```

Two modes via `--mode` flag:

**`--mode calibrate`** — refit temperature scalar and thresholds only. No model retraining.
Use when < 500 new labeled samples have accumulated. Fast (< 2 min for either model type).

**`--mode full`** (default) — full pipeline. Use when ≥ 500 new labeled samples have
accumulated or override rate has breached threshold.

**`src/training/train.py`** — training logic, importable as a module. Reads `model.type`
from config, dispatches to the right trainer. Contains no routing or serving logic.

**`src/training/evaluate.py`** — standalone evaluation. Can be called from `retrain.py`
or run independently:
```bash
python scripts/evaluate_model.py --checkpoint checkpoints/transformer-v1.0
```

---

### 6. Model Artifact Versioning

```
checkpoints/
  lgbm-v1.0/
    manifest.json         → model_type, version, training_date, dataset_version, metrics
    temperature.json      → {"T": 1.42}
    model.txt             → LightGBM model
    vectorizer.pkl        → TF-IDF vectorizer
  transformer-v1.0/
    manifest.json
    temperature.json
    model.pt              → PyTorch checkpoint
    tokenizer/            → HuggingFace tokenizer files
  production -> transformer-v1.0    (symlink — what the API loads)
```

The API reads `manifest.json` at startup to instantiate the correct adapter. Promoting a
new model:

```bash
python scripts/promote_model.py --checkpoint checkpoints/transformer-v1.0
# updates symlink, logs the promotion event, signals API restart
```

No code changes. No redeployment. `manifest.json` in every checkpoint is the full audit
trail.

---

### 7. Configuration (`configs/`)

```
configs/
  base.yaml         → log level, data paths, latency budget
  train.yaml        → model.type, hyperparameters, feature list
  inference.yaml    → checkpoint path, async attribution flag
  thresholds.yaml   → routing bands, security override threshold
```

`thresholds.yaml` is the primary operational lever — routing sensitivity adjusted without
code changes. `train.yaml → model.type` is the model switch — change it and run
`retrain.py` to produce a checkpoint of the new type. Nothing else changes.

---

### 8. Explainability

Delivered through `feature_attributions` in `ModelOutput`. The adapter computes
attributions in whatever way suits the model type. The rule summariser that converts scores
to human-readable reasons operates on the dict only — it has no model knowledge.

- **LightGBM adapter:** SHAP on structured features. Inline, < 10ms.
- **Transformer adapter:** SHAP on structured MLP features inline. Integrated Gradients on
  text encoder dispatched as a background task, result pushed to analyst interface async.

---

### 9. Monitoring

`GET /metrics` (Prometheus format):

- `emails_triaged_total` — counter, labelled by routing decision
- `analyst_review_rate` — gauge, 7-day rolling
- `override_rate` — gauge, 7-day rolling
- `inference_latency_ms` — histogram
- `model_version` — info metric
- `retrain_events_total` — counter

Plugs into any standard stack (Grafana, Datadog, CloudWatch) or ignored entirely.

---

## What Is Not In Scope (v1)

- **Analyst web interface** — system provides `POST /feedback` and `GET /feedback/queue`.
  Client integrates their existing SOC tooling against those endpoints.
- **Distributed training** — single-machine retraining is sufficient at this scale. GPU via
  cloud notebook is the ceiling for transformer runs.
- **Orchestration** — ships as Docker. Kubernetes/ECS is a client infrastructure concern.
- **Multi-tenancy** — single-tenant. Replicate the stack per tenant if required.
- **Automatic retraining** — drift_detector logs the trigger condition. Human decides to
  run `retrain.py`. Fully automated retraining without oversight is not appropriate for a
  security classification system.

---

## Technology Choices

| Component | Choice | Reason |
|-----------|--------|--------|
| API | FastAPI | Async, background tasks, Pydantic validation, OpenAPI free |
| Model interface | Python Protocol | Structural typing, zero base class coupling |
| Feedback store | SQLite → Postgres | Zero-dependency v1, identical migration path |
| Containerisation | Docker | Portable, client-deployable, no lock-in |
| Config | YAML + Pydantic | Human-readable, validated at startup |
| Monitoring | Prometheus endpoint | Standard, opt-in, zero infrastructure requirement |
| Artifact versioning | Filesystem + symlink | Simple, auditable, no registry at v1 |

No message queues, no feature stores, no model registries at v1. The system is designed to
be handed to a client and operated without specialist MLOps infrastructure.
