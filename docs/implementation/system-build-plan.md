# System Build Plan — Inference Pipeline & Surrounding System
Date: 2026-06-14. Updated: 2026-06-17. Status: Phases A–F complete. Pending: production artifact export.

## Context

Model training is complete. LightGBM (Phase 2) is the production model. This document covers everything needed to make the model operational: the inference pipeline, REST API, feedback store, retraining scripts, and demo UI.

The central design principle from `engineering-system.md`: **the model is a plugin**. The API, router, and retraining pipeline depend only on the `ModelAdapter` Protocol — never on a concrete adapter.

---

## Phase A — Core Pipeline ✅ Complete

Goal: produce a `TriageResponse` from a raw email with no HTTP layer. This is the hardest phase. Everything else is wiring.

### A1 — Email Parser (`src/parsing/`) ✅
- Accept raw `.eml` (via `email` stdlib) or pre-parsed JSON
- Output: normalized `ParsedEmail` dataclass with `subject`, `body_text`, `from_addr`, `reply_to`, `headers`, `urls`, `attachments`

### A2 — Feature Extractor (`src/features/`) ✅
- Wire existing feature modules into `feature_pipeline.py`
- Output: fully-populated `dict[str, float]` — no nulls, missing = `0` / `False`
- Modules: `sender_features.py`, `url_features.py`, `attachment_features.py`, `text_stats.py`, `brand_features.py`

### A3 — Model Adapter (`src/inference/predictor.py`) ✅
- Define `ModelAdapter` Protocol:
  ```python
  class ModelAdapter(Protocol):
      def predict(self, text: str, features: dict[str, float]) -> ModelOutput: ...
      def version(self) -> str: ...
      def model_type(self) -> str: ...

  @dataclass
  class ModelOutput:
      spam_prob: float
      phishing_prob: float
      feature_attributions: dict[str, float]
  ```
- Implement `LightGBMAdapter`: load `model.txt` + `vectorizer.pkl` → TF-IDF → LightGBM → SHAP attributions
- Adapter loaded from `checkpoints/production/manifest.json` at startup

### A4 — Confidence Router (`src/inference/threshold_router.py`) ✅
- Stateless: `(spam_prob, phishing_prob, T) → RoutingDecision`
- Trust score: `trust_score = 0.6 * max_prob + 0.4 * margin_score`, normalized 0–100
- Routing bands (from `configs/thresholds.yaml`):
  - `>90`: Auto-classify
  - `75–90`: Auto-classify + monitoring flag
  - `55–75`: Analyst Review
  - `<55`: Priority Analyst Review
- Security override: `phishing_prob > 0.70` AND high-weight signal present → immediate escalation

### A5 — Postprocessor (`src/inference/postprocess.py`) ✅
- Assemble `TriageResponse` from `ModelOutput` + `RoutingDecision`
- Feed attributions to rule summarizer → populate `reasons[]` and `confidence_notes[]`

### A6 — Rule Summarizer (`src/explainability/rule_summarizer.py`) ✅
- Map SHAP attribution keys → human-readable `reasons[]`
- Deterministic and auditable — consistent across model versions

---

## Phase B — REST API ✅ Complete

### B1 — Pydantic Schemas (`src/serving/schemas.py`) ✅
- `TriageRequest`, `TriageResponse`, `FeedbackRequest`, `FeedbackResponse`
- Match spec in `docs/operations/api-integration.md` exactly

### B2 — FastAPI App (`src/serving/api.py`) ✅
Endpoints:
- `POST /triage` — accept `.eml` or JSON → run full pipeline → return `TriageResponse`
- `POST /feedback` — store analyst verdict
- `GET /feedback/queue` — return emails awaiting review, ordered by trust score ascending, paginated
- `GET /health` — `{status, model_version}`
- `GET /model/info` — version, type, training date, dataset version, key metrics
- `GET /metrics` — Prometheus-format counters and latency histograms

---

## Phase C — Feedback Store ✅ Complete

### C1 — SQLite Store (`src/feedback/store.py`) ✅
Key schema fields: `id`, `email_id`, `received_at`, `model_version`, `subject`, `body_text`, `features` (JSON), `predicted_label`, `spam_prob`, `phishing_prob`, `trust_score`, `analyst_label`, `analyst_id`, `reviewed_at`, `notes`, `agreement`.
- Store both `body_text` (for transformer retraining) and `features` JSON (for LightGBM retraining)
- SQLite v1; Postgres is a one-line config swap

### C2 — Drift Detector (`src/feedback/drift_detector.py`) ✅
- Rolling 7-day override rate monitor
- Log retrain trigger when override rate > 20%
- Does NOT auto-retrain — signals only; human decides

---

## Phase D — Retraining & Artifact Management ✅ Complete

### D1 — Retrain Script (`scripts/retrain.py`) ✅
Two modes:
- `--mode calibrate`: refit temperature scalar only, <2 min, use when <500 new samples
- `--mode full` (default): load base data → merge feedback (feedback labels take precedence) → train → calibrate → evaluate → gate (new phishing recall ≥ current production) → save artifacts

### D2 — Promote Script (`scripts/promote_model.py`) ✅
- Update `checkpoints/production` symlink to new versioned checkpoint
- Log promotion event with timestamp, model version, and evaluation metrics
- Signal API restart

Artifact layout:
```
checkpoints/
  {model}-v{X.Y}/
    manifest.json
    temperature.json
    [model artifacts]
  production -> checkpoints/{model}-v{X.Y}  (symlink)
```

---

## Phase E — Demo UI ✅ Complete

Minimal 3-page interface for client demonstration (see `docs/operations/demonstration.md`):

- **Triage Page** (`/demo/`): paste raw email text → POST /triage → result card (label, trust score, probabilities, reasons)
- **Review Queue Page** (`/demo/queue`): GET /feedback/queue → list ordered most uncertain first, click to open verdict
- **Verdict Page** (`/demo/verdict/{id}`): full triage result + Confirm / Override → Phishing / Override → Spam / Defer → POST /feedback

Served as Jinja2 templates via FastAPI. No auth. Demo-only artifact, not part of production API surface.

---

## Phase F — Packaging ✅ Complete

- `Dockerfile` — single container, `python:3.12-slim`, copies `src/`, `configs/`, `checkpoints/production/`, `data/assets/`
- `docker-compose.yml` — volume mounts for `data/` and `checkpoints/` (feedback persists; promoted models load without rebuild)
- `configs/base.yaml` — log level, data paths
- `configs/inference.yaml` — checkpoint path, async attribution flag
- `configs/thresholds.yaml` — routing bands, override threshold
- `configs/train.yaml` — `model.type`, hyperparameters, feature list

---

## Execution Order

```
A1 → A2 → A3 → A4 → A5 → A6   (pipeline, no HTTP)     ✅ done
B1 → B2                          (API layer)              ✅ done
C1 → C2                          (feedback store)         ✅ done
D1 → D2                          (retraining)             ✅ done (20 tests)
E                                 (demo UI)                ✅ done
F                                 (packaging, last)        ✅ done
```

**Remaining before first run:** export production model artifacts — see `docs/implementation/left.md`.

---

## Test Coverage

149 tests, all passing as of 2026-06-17.

| Suite | Tests | Status |
|---|---|---|
| `test_features.py` | 22 | ✅ |
| `test_threshold_router.py` | 18 | ✅ |
| `test_postprocess.py` | 14 | ✅ |
| `test_rule_summarizer.py` | 14 | ✅ |
| `test_feedback_store.py` | 20 | ✅ |
| `test_drift_detector.py` | 8 | ✅ |
| `test_pipeline_integration.py` | 14 | ✅ |
| `test_api.py` | 19 | ✅ |
| `test_retrain.py` | 20 | ✅ |

---

## Constraints

- API and router never import concrete adapters — `ModelAdapter` Protocol only
- Feature pipeline always produces a fully-populated dict — no partial feature sets
- No automatic model promotion — human gates every deployment
- SQLite first; Postgres when concurrent analyst load warrants it
