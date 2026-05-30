# Phase 3 Decision Report — Should We Build the Transformer?

**Date:** 2026-05-31
**Decision Required By:** Team
**Context:** Phases 1, 2, and 2b are complete. This document presents the case for and against proceeding to Phase 3 (hybrid RoBERTa + MLP transformer architecture).

---

## 1. Where We Are

### Current System (Phase 2 + 2b — LightGBM)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Phishing Recall | 98.13% | > 98% | ✅ Met |
| Accuracy | 97.68% | — | ✅ |
| ROC-AUC | 0.9959 | — | ✅ |
| Auto-classify rate | 96.8% | — | ✅ |
| Phishing recall (auto) | 98.92% | — | ✅ |
| Analyst review rate | 3.2% | Minimise | ✅ |
| ECE (calibration) | 0.4455 | < 0.05 | ❌ Not met |
| Inference latency | Not benchmarked | < 300ms | Pending |

**The primary project target (>98% phishing recall) is met. The only failing metric is ECE.**

---

## 2. What Phase 3 Is

Phase 3 is a **hybrid transformer architecture**:

```
Text Encoder (RoBERTa fine-tuned on email subject + body)
+
Structured Feature Encoder (MLP on 19 engineered features)
+
Fusion Layer
+
Binary Classification Head
```

This is the "future-state architecture" defined in `docs/design/ai-solutions.md`. It was always intended as exploratory — only to be built if Phase 2 performance was insufficient.

---

## 3. The Case FOR Phase 3

### 3.1 Calibration is broken and cannot be fixed otherwise
ECE = 0.4455 vs target < 0.05. Post-hoc calibration (Platt, temperature scaling) cannot fix this on LightGBM + TF-IDF. A transformer with softmax output and cross-entropy training produces well-calibrated probabilities by design. This is the only known path to meeting the ECE target.

**Why ECE matters operationally:** The trust score thresholds (which drive routing decisions) are computed from probabilities. With ECE = 0.44, a "90% confident phishing" prediction does not actually mean 90% confidence. The routing bands work correctly in practice (because the model's discrimination is strong), but the confidence scores cannot be trusted as absolute probability estimates. This matters for:
- Analyst-facing explanations ("the model is 94% confident this is phishing")
- Threshold tuning in production as email patterns evolve
- Feedback loop integration (analyst verdicts weighted by model confidence)

### 3.2 Semantic understanding of modern attack patterns
LightGBM + TF-IDF learns word frequencies. It cannot understand:
- Paraphrased phishing language ("kindly verify your credentials" vs "please confirm your login")
- Context-dependent urgency ("your account will be suspended" in a legitimate vs phishing context)
- BEC-style emails with no URLs, no attachments, and subtle impersonation language

RoBERTa's contextual embeddings capture semantic meaning, not just word presence. This is particularly important for BEC (Business Email Compromise) — the hardest phishing subtype, which relies entirely on text signals.

### 3.3 Marginal recall improvement is still valuable
Phase 2 is at 98.13% phishing recall. The project target is >98%. There is almost no headroom. A transformer could push this to 99%+, which at SOC scale (thousands of emails per day) means dozens fewer missed phishing emails per day.

### 3.4 Production architecture alignment
The design document (`docs/design/ai-solutions.md`) specifies the transformer as the target production architecture. Building it validates the full system design and produces the model intended for long-term deployment.

---

## 4. The Case AGAINST Phase 3

### 4.1 The primary target is already met
Phishing recall > 98% is achieved. The project goal is met. Phase 3 is not required to deliver a working system.

### 4.2 Significant engineering complexity
Phase 3 requires:
- GPU compute (Kaggle GPU sessions, limited quota)
- RoBERTa fine-tuning (hours of training time)
- Handling long emails (truncation strategy, head+tail retention, or hierarchical chunking)
- Two-tier inference pipeline (inline structured features + async text attribution)
- More complex deployment (PyTorch model vs LightGBM .txt file)

### 4.3 Latency risk
The < 300ms inline inference target is comfortable for LightGBM. A transformer adds significant latency. Dedicated benchmarking would be required, and the architecture may need modification (distillation, quantisation) to meet the target.

### 4.4 Calibration may not improve enough to matter
Even if ECE improves to < 0.05, the routing outcomes are already correct. The practical benefit of better calibration is incremental — better analyst-facing confidence scores and more reliable threshold tuning, but not a step-change in SOC effectiveness.

### 4.5 Dataset limitations cap the ceiling
The dataset has known structural limitations (sparse header features, Enron artifacts, limited BEC coverage). A transformer will learn better text representations but is still constrained by the same data. The marginal gain may be smaller than expected.

---

## 5. Risk Assessment

| Risk | Phase 2 (LightGBM) | Phase 3 (Transformer) |
|------|-------------------|----------------------|
| Calibration failure | ❌ ECE = 0.44 | ✅ Expected < 0.05 |
| Phishing recall | ✅ 98.13% | ✅ Expected ≥ 99% |
| Inference latency | ✅ Comfortable | ⚠️ Needs benchmarking |
| Deployment complexity | ✅ Simple | ⚠️ Complex |
| Training time | ✅ Minutes | ⚠️ Hours (GPU) |
| Explainability | ✅ SHAP (fast) | ⚠️ Integrated Gradients (async) |
| Production readiness | ✅ Ready | ⚠️ Requires more work |

---

## 6. Recommendation

**Proceed to Phase 3, but treat it as exploratory.**

The calibration failure is a real problem for a production system. The ECE target exists for a reason — it affects analyst trust, threshold stability, and feedback loop quality. LightGBM cannot meet it. Phase 3 is the only path to fixing it.

However, Phase 3 should be time-boxed. If the transformer does not materially improve calibration (ECE < 0.10 at minimum, ideally < 0.05) or introduces unacceptable latency, Phase 2 is the production model.

### Decision Criteria for Phase 3 Success

| Criterion | Threshold | Priority |
|-----------|-----------|----------|
| ECE | < 0.10 (acceptable), < 0.05 (target) | High |
| Phishing Recall | ≥ 98.5% | High |
| Inference latency | < 300ms inline | High |
| Accuracy | ≥ 98% | Medium |
| Auto-classify rate | ≥ 95% | Medium |

If Phase 3 meets all High priority criteria, it replaces Phase 2 as the production model. If it fails any High priority criterion, Phase 2 remains the production model.

---

## 7. Phase 3 Implementation Plan

If proceeding:

1. **Text encoder:** Fine-tune `roberta-base` on the training set (subject + body, truncated to 512 tokens with head+tail strategy for long emails)
2. **Structured encoder:** 3-layer MLP on the 19 engineered features
3. **Fusion:** Concatenate RoBERTa [CLS] embedding + MLP output → binary classification head
4. **Training:** AdamW, linear warmup + cosine decay, weighted cross-entropy (higher penalty for phishing false negatives)
5. **Calibration:** Temperature scaling on the validation set (expected to work properly with transformer outputs)
6. **Explainability:** SHAP on structured features (inline), Integrated Gradients on text (async)
7. **Latency benchmark:** Measure end-to-end inference time before declaring production-ready

**Estimated GPU time on Kaggle:** 2–4 hours for fine-tuning.

---

## 8. Summary

| Question | Answer |
|----------|--------|
| Is Phase 2 good enough to ship? | Yes, for classification. No, for calibration. |
| Is Phase 3 required? | Not strictly, but recommended to fix calibration. |
| What does Phase 3 fix? | ECE (calibration), semantic understanding, BEC detection |
| What does Phase 3 risk? | Latency, complexity, training time |
| What is the go/no-go criterion? | ECE < 0.10 AND recall ≥ 98.5% AND latency < 300ms |
