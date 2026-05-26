# Model Development Plan

## 1. Objective

This document defines the model development strategy for the Barclays suspicious email triage system.

The system classifies user-reported suspicious emails into two semantic classes:

- **Spam**
- **Phishing**

A third operational outcome, **Analyst Review**, is not a training label. It is determined post-inference through confidence-based routing.

Primary objective:

> Reduce SOC analyst triage burden by safely automating high-confidence spam/phishing decisions while escalating ambiguous or high-risk cases for manual review.

---

# 2. Development Principles

Model development prioritizes:

- operational reliability
- explainability
- low false-negative phishing risk
- deployability in enterprise environments
- confidence-aware fail-safe routing
- reproducibility
- measurable latency constraints

Accuracy alone is not sufficient.

A marginally more accurate but opaque or operationally unsafe model is not preferred.

---

# 3. Dataset Summary

Final cleaned dataset:

| Split | Samples |
|------|--------:|
| Train | 15,483 |
| Validation | 3,188 |
| Test | 3,189 |
| Total | 21,860 |

Dataset integrity validation completed.

Resolved issues:

- cross-split duplicate leakage removed
- synthetic augmentation leakage removed from evaluation
- source distribution drift corrected
- provenance leakage features removed
- duplicate IDs removed
- schema consistency verified

Task framing:

**Binary classification: Spam vs Phishing**

This is not a benign-vs-malicious email detection problem.

---

# 4. Feature Set

## 4.1 Text Inputs

Raw semantic inputs:

- `subject`
- `body_text`

Combined into a unified text representation.

---

## 4.2 Structured Features

### Sender Signals

- `display_from_mismatch`
- `reply_to_mismatch`
- `free_email_sender`

---

### URL Signals

- `url_count`
- `domain_count`
- `shortened_url_present`
- `suspicious_tld_present`
- `ip_literal_url`
- `url_entropy`
- `typosquatting_detected`

---

### Attachment Signals

- `has_attachment`
- `executable_detected`
- `macro_detected`

---

### Statistical Text Signals

- `subject_length`
- `body_length`
- `uppercase_ratio`
- `digit_ratio`
- `punctuation_density`
- `link_density`

---

### Brand Signals

- `brand_mention`
- `sender_brand_mismatch`

---

# 5. Excluded Features

The following fields are intentionally excluded.

| Feature | Reason |
|--------|--------|
| `id` | Identifier leakage / non-generalizable |
| `split` | Direct leakage |
| `source` | Dataset provenance leakage |
| `augmented` | Synthetic sample leakage |
| `attachment_type` | Extremely sparse / low utility |
| `subtype` | Sparse / provenance-adjacent |
| `era_bucket` | Inconsistent semantics |

---

# 6. Label Encoding

Encoding:

```python
spam = 0
phishing = 1
```

Rationale:

Phishing is the higher-risk positive class.

This simplifies:

- recall interpretation
- threshold tuning
- false negative analysis

---

# 7. Model Development Strategy

Development proceeds in staged phases.

---

# Phase 1 — Baseline Benchmark

## Model

Logistic Regression

## Inputs

- TF-IDF vectorized text (`subject + body_text`)
- structured engineered features

## Purpose

Establish a fast, interpretable baseline.

This benchmark answers:

- can classical ML solve the task effectively?
- what is the minimum viable performance?
- which features dominate predictions?

## Why this phase exists

Benefits:

- rapid iteration
- explainability
- calibration friendliness
- low engineering complexity
- useful benchmark for later comparison

Expected outcome:

A credible baseline, not final production architecture.

---

# Phase 2 — Enterprise Candidate Model

## Model

LightGBM

(Alternative benchmark: XGBoost)

## Inputs

- TF-IDF text vectors
- structured engineered features

## Rationale

This is the primary production candidate.

Advantages:

- strong nonlinear learning
- excellent sparse feature handling
- efficient inference
- SHAP explainability support
- operational maturity
- low latency
- robust deployment profile

This model balances performance with enterprise operational requirements.

---

# Phase 3 — Advanced Semantic Model

## Model

Hybrid transformer architecture.

Design:

```text
Text Encoder (RoBERTa)
+
Structured Feature Encoder (MLP)
+
Fusion Layer
+
Binary Classification Head
```

## Purpose

Future-state architecture.

This phase evaluates whether deep semantic modeling materially improves performance beyond the enterprise candidate.

Tradeoffs:

- higher engineering complexity
- higher latency
- more difficult calibration
- more complex explainability

This phase is exploratory unless Phase 2 performance is insufficient.

---

# 8. Text Processing Strategy

## Phase 1 / 2

Text pipeline:

```text
subject + separator + body_text
```

Vectorization:

TF-IDF

Preprocessing:

- lowercase normalization
- whitespace normalization
- optional stopword evaluation
- preserve security-relevant tokens
- preserve URLs
- preserve suspicious lexical patterns

Avoid aggressive cleaning that removes phishing signals.

Do not strip:

- domains
- URLs
- account identifiers
- urgency markers

---

## Phase 3

Transformer tokenizer:

RoBERTa tokenizer

Handling long emails:

Candidate strategies:

- truncation
- head + tail retention
- hierarchical chunking

Decision deferred until Phase 3.

---

# 9. Structured Feature Processing

Numeric preprocessing:

- scaling where required
- boolean encoding
- missing value verification

Candidate scalers:

- StandardScaler
- MinMaxScaler

Model-dependent selection:

- Logistic Regression requires scaling
- LightGBM generally does not

---

# 10. Class Imbalance Handling

Observed distribution:

- Spam: ~45.5%
- Phishing: ~54.5%

This is acceptably balanced.

Initial approach:

No aggressive rebalancing.

Evaluate:

- standard training
- optional class weighting

Apply weighting only if phishing recall suffers.

---

# 11. Evaluation Metrics

Accuracy is not the primary metric.

---

## Primary Metrics

### Phishing Recall

Critical metric.

Definition:

> Percentage of phishing emails correctly identified.

Reason:

False negatives are operationally expensive.

---

### Phishing Precision

Definition:

> Of emails predicted as phishing, how many are truly phishing.

Reason:

Low precision overwhelms analysts.

---

### F1 Score

Balanced precision/recall assessment.

---

### PR-AUC

Preferred over ROC-AUC for risk-sensitive classification.

---

# Secondary Metrics

- Accuracy
- ROC-AUC
- confusion matrix

---

# Calibration Metrics

Required for confidence routing.

- Expected Calibration Error (ECE)
- Brier Score
- reliability diagram

Target:

```text
ECE < 0.05
```

after calibration.

---

# 12. Confidence Layer Development

The classifier outputs calibrated probabilities.

Confidence scoring:

```python
trust_score = w1 * max_prob + w2 * margin_score
```

Where:

- `max_prob` = highest calibrated class probability
- `margin_score` = separation between class probabilities

Default:

```python
w1 = 0.6
w2 = 0.4
```

---

## Routing Thresholds

| Trust Score | Action |
|---|---|
| > 90 | Auto-classify |
| 75–90 | Auto-classify + monitoring |
| 55–75 | Analyst Review |
| < 55 | Priority Analyst Review |

---

## Security Override

Immediate escalation if:

```python
phishing_probability > 0.70
```

AND high-risk signal present:

- credential request
- typosquatting
- executable attachment
- macro attachment
- IP literal URL
- executive impersonation + financial fraud indicators

---

# 13. Explainability Plan

## Phase 1 / 2

Primary explainability:

SHAP

Outputs:

- top contributing structured features
- confidence notes
- deterministic rule-based reasons

Examples:

- reply-to mismatch detected
- suspicious URL entropy
- free-email sender impersonation
- credential request language

---

## Phase 3

Additional text explainability:

Integrated Gradients

Delivered asynchronously.

---

# 14. Experiment Tracking

Track:

- model version
- preprocessing config
- feature configuration
- hyperparameters
- calibration version
- threshold settings
- evaluation metrics
- analyst routing rate

Suggested tooling:

- MLflow
- Weights & Biases
- structured experiment manifests

---

# 15. Validation Methodology

Training:

Train set only

Hyperparameter tuning:

Validation set only

Final reporting:

Held-out test set only

Strict separation required.

No test set tuning.

---

# 16. Deployment Constraints

Target:

```text
<300ms inline inference
```

Operational pipeline:

```text
email parse
→ feature extraction
→ inference
→ calibration
→ trust score
→ routing
→ explanation
```

Phase 1 / 2 expected to comfortably satisfy latency requirements.

Phase 3 requires dedicated benchmarking.

---

# 17. Recommended Delivery Path

Execution order:

1. Logistic Regression baseline
2. LightGBM enterprise candidate
3. calibration + confidence routing
4. SHAP explainability
5. threshold tuning with SOC scenarios
6. transformer comparison (optional advanced phase)

---

# 18. Success Criteria

Minimum technical success:

- phishing recall > target threshold
- acceptable analyst review rate
- calibrated confidence outputs
- stable inference latency
- explainable decision outputs

Operational success:

- reduced analyst workload
- safe escalation of ambiguous emails
- low false-negative phishing rate
- deployable enterprise architecture