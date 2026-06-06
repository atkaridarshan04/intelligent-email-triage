# Final Model Decision — Production Model Selection

**Date:** 2026-05-31
**Status:** Final — Model training phase complete

---

## Decision

**Phase 2 (LightGBM) is the production model.**

---

## Evidence

Three models evaluated across Phases 1–3:

| Model | Phishing Recall | ECE | Decision |
|-------|----------------|-----|----------|
| Logistic Regression (Phase 1) | 94.38% | 0.40 | ❌ Recall too low |
| **LightGBM (Phase 2)** | **98.01%** | **0.44** | **✅ Production** |
| RoBERTa+MLP (Phase 3, 3 runs) | 96.19–97.01% | 0.39–0.40 | ❌ Worse than Phase 2 |

Phase 3 was run three times with different configurations (baseline, label smooth + mixup, label smooth only). All three runs produced worse classification metrics than Phase 2 and did not materially improve ECE.

---

## Why LightGBM

- Only model to meet the >98% phishing recall target ✅
- Best on every classification metric ✅
- 98.8% auto-classification rate — minimal analyst burden ✅
- Fast inference, simple deployment (.txt file), SHAP explainability ✅
- ECE failure is shared by all models — it is a dataset property

---

## The Calibration Situation

ECE ≈ 0.39–0.45 across all three model families. This is not fixable by model choice or training technique. The dataset is too cleanly separable — spam and phishing use sufficiently different language that any model becomes overconfident.

**Practical impact:** The routing system works correctly in practice. 96.8% auto-classification with 98.92% phishing recall within auto-classified emails. The ECE failure affects confidence score accuracy but not routing outcomes.

**Fix:** Collect ambiguous analyst-reviewed emails post-deployment and retrain with label smoothing. This is a future iteration task via the feedback loop.

---

## Production Model Artifacts

| Artifact | Location |
|----------|----------|
| LightGBM model | `checkpoints/production/` (to be saved) |
| TF-IDF vectorizer | `artifacts/tokenizer/` (to be saved) |
| Calibration (temperature) | `artifacts/thresholds/` (to be saved) |
| SHAP explainer | Generated at inference time |

---

## What Comes Next

Model training is complete. Next phase: production inference pipeline.

1. **Inference pipeline** — email parsing → feature extraction → LightGBM → trust score → routing
2. **REST API** — FastAPI endpoint accepting email, returning routing decision + explanation
3. **Feedback loop** — analyst verdicts → retraining queue
4. **Monitoring** — performance tracking, drift detection
5. **Calibration improvement** — retrain with analyst feedback data + label smoothing (future)
