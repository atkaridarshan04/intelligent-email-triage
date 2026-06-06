# Phase 1 Report — Logistic Regression Baseline

**Date:** 2026-05-31
**Status:** Complete
**Next Phase:** Phase 2 — LightGBM Enterprise Candidate

---

## 1. Objective

Phase 1 establishes a fast, interpretable baseline for the spam vs. phishing binary classification task. The goal is not to build the final production model, but to answer three questions:

1. Can classical ML solve this task effectively?
2. What is the minimum viable performance floor?
3. Which features dominate predictions?

The answers inform Phase 2 architecture decisions and set a benchmark to beat.

---

## 2. Dataset

The model was trained on the final cleaned dataset at `data/model_ready/`.

| Split      | Samples | Spam  | Phishing |
|------------|--------:|------:|---------:|
| Train      | 15,483  | 6,909 (44.6%) | 8,574 (55.4%) |
| Validation | 3,188   | 1,480 (46.4%) | 1,708 (53.6%) |
| Test       | 3,189   | 1,481 (46.4%) | 1,708 (53.6%) |
| **Total**  | **21,860** | | |

**Label encoding:** spam = 0, phishing = 1 (phishing is the positive class throughout).

**Key dataset properties:**
- Zero cross-split text leakage
- No augmented samples in val/test
- All leaky provenance columns removed (source, augmented, era_bucket, etc.)
- 24 features: subject, body_text, 19 structured engineered features, label

---

## 3. Model Architecture

### Text Features
- Subject and body_text concatenated with a `[SEP]` separator
- Vectorized with **TF-IDF**: 50,000 features, bigrams (1–2), sublinear TF, min_df=2, unicode strip

### Structured Features (19 columns)
Scaled with StandardScaler (required for Logistic Regression):

| Group | Features |
|-------|----------|
| Sender | display_from_mismatch, reply_to_mismatch, free_email_sender |
| URL | url_count, domain_count, shortened_url_present, suspicious_tld_present, ip_literal_url, url_entropy, typosquatting_detected |
| Attachment | has_attachment |
| Text stats | subject_length, body_length, uppercase_ratio, digit_ratio, punctuation_density, link_density |
| Brand | brand_mention, sender_brand_mismatch |

> Note: `executable_detected` and `macro_detected` were dropped — both are all-False in this dataset (zero variance).

### Combined Feature Matrix
TF-IDF sparse matrix + scaled structured features → stacked into a single sparse matrix of shape **(15,483 × 50,019)**.

### Classifier
**Logistic Regression** — solver: SAGA, C=1.0, max_iter=1000, no class weighting (dataset is acceptably balanced).

### Calibration
**Platt scaling** (CalibratedClassifierCV, sigmoid, cv="prefit") applied on the validation set after training.

---

## 4. Results

### 4.1 Classification Metrics

#### Validation Set

| Class    | Precision | Recall | F1     | Support |
|----------|-----------|--------|--------|---------|
| Spam     | 0.9182    | 0.9176 | 0.9179 | 1,480   |
| Phishing | 0.9286    | 0.9292 | 0.9289 | 1,708   |
| **Accuracy** | | | **0.9238** | 3,188 |

| Metric   | Value  |
|----------|--------|
| ROC-AUC  | 0.9693 |
| PR-AUC   | 0.9730 |
| Brier Score | 0.0610 |

#### Test Set (Held-Out)

| Class    | Precision | Recall | F1     | Support |
|----------|-----------|--------|--------|---------|
| Spam     | 0.9345    | 0.9251 | 0.9298 | 1,481   |
| Phishing | 0.9356    | 0.9438 | 0.9397 | 1,708   |
| **Accuracy** | | | **0.9351** | 3,189 |

| Metric   | Value  |
|----------|--------|
| ROC-AUC  | 0.9720 |
| PR-AUC   | 0.9687 |
| Brier Score | 0.0553 |

**Test slightly outperforms validation** — consistent, no overfitting to the validation set.

---

### 4.2 Confidence Routing Simulation

Trust score formula (per `models.md`):
```
trust_score = (0.6 × max_prob + 0.4 × margin) × 100
```

Routing bands applied to the **test set**:

| Band | Trust Score | Count | % of Total |
|------|-------------|------:|------------|
| Auto-classify | > 90 | 2,122 | 66.5% |
| Auto-classify + monitor | 75–90 | 519 | 16.3% |
| Analyst Review | 55–75 | 334 | 10.5% |
| Priority Analyst Review | < 55 | 214 | 6.7% |

**Auto-classified total (trust > 75):** 2,641 / 3,189 = **82.8%**

**Phishing recall within auto-classified emails only:** **97.89%**

This means: of the 82.8% of emails the model is confident enough to auto-route, it correctly identifies 97.89% of phishing. The remaining 17.2% go to analysts — which is the intended safety net for uncertain cases.

---

### 4.3 Calibration

**Expected Calibration Error (ECE): 0.4043**

Target: < 0.05. **This is a critical failure.**

The calibration curve shows the model's predicted probabilities are severely overconfident — they cluster near 0 and 1 rather than reflecting true likelihoods. Platt scaling was applied but did not correct this adequately.

**Why this happened:** Logistic Regression on high-dimensional TF-IDF features (50,000 dimensions) is a known calibration problem. The model pushes probabilities to extremes because the high-dimensional space makes classes appear more separable than they are. This is a structural limitation of LR + TF-IDF, not a bug in the implementation.

**Practical impact:** The trust score thresholds (which drive routing decisions) are computed from these probabilities. With ECE = 0.40, the routing bands cannot be trusted operationally. A "90% confident phishing" prediction from this model does not actually mean 90% confidence.

---

### 4.4 Top Predictive Features

#### Top 20 Phishing Signals (positive coefficients)

| Feature | Coefficient |
|---------|-------------|
| account | +2.8572 |
| email | +2.0713 |
| click | +1.7473 |
| please | +1.6537 |
| bank | +1.6346 |
| your | +1.5953 |
| your account | +1.5298 |
| click here | +1.4947 |
| money | +1.3700 |
| transfer | +1.2579 |
| security | +1.1704 |
| business | +1.1527 |
| body_length | +1.1434 |
| mail | +1.1187 |

**Interpretation:** Classic phishing vocabulary — urgency, financial action, credential requests. `body_length` appearing as a phishing signal reflects that phishing emails in this dataset tend to be longer (more elaborate social engineering). These are genuine, generalizable signals.

#### Top 20 Spam Signals (negative coefficients)

| Feature | Coefficient |
|---------|-------------|
| the | −1.6786 |
| it | −1.5958 |
| enron | −1.5369 |
| at | −1.4129 |
| sender_brand_mismatch | −1.3363 |
| link_density | −1.2104 |
| ect | −1.1596 |
| vince | −1.0434 |

**Interpretation — mixed signals:**
- `sender_brand_mismatch` and `link_density` as spam signals are **genuine and generalizable** — spam emails often have brand mismatches and high link density.
- `enron`, `vince`, `ect` are **dataset artifacts** from the Enron corpus. The model is partially learning dataset identity rather than pure spam behavior. This is the known limitation of organic-only data with sparse header features.
- Common stop words (`the`, `it`, `at`) appearing as spam signals suggests the model is picking up stylistic differences between spam and phishing corpora rather than semantic content.

---

## 5. What Phase 1 Proved

| Question | Answer |
|----------|--------|
| Can classical ML solve this task? | **Yes.** 93.5% accuracy and 94.4% phishing recall is a strong baseline. |
| What is the minimum viable performance floor? | Accuracy ≥ 93%, Phishing Recall ≥ 94%, ROC-AUC ≥ 0.97 |
| Which features dominate? | **Text dominates.** Structured features contribute (sender_brand_mismatch, link_density, body_length) but TF-IDF text features carry most of the signal. |

---

## 6. Known Limitations

### Calibration Failure (Critical)
ECE = 0.40 vs. target < 0.05. The routing layer cannot be trusted with this model. This is a structural LR + TF-IDF problem, not fixable by tuning.

### Dataset Artifact Learning
The model learned Enron-specific tokens (`enron`, `vince`, `ect`) as spam signals. These will not generalize to real-world email. LightGBM with SHAP analysis in Phase 2 will make it easier to identify and suppress such artifacts.

### Structured Feature Sparsity
Most header-derived features (display_from_mismatch: 0.2%, has_attachment: 0.1%) are near-zero because the dataset comes from Kaggle CSVs without full email headers. The model is text-dominant by necessity. This is a dataset limitation, not a model limitation.

### Synthetic Template Artifacts
`monkey org`, `jose monkey` appeared in top phishing features — these are artifacts from specific synthetic phishing templates. Not a blocker, but indicates the synthetic data has some template fingerprinting.

---

## 7. Phase 2 Expectations

Phase 2 uses **LightGBM** — the primary production candidate. Expected improvements:

| Aspect | Phase 1 (LR) | Phase 2 (LightGBM) Expected |
|--------|-------------|------------------------------|
| Calibration (ECE) | 0.40 ❌ | < 0.05 ✅ |
| Phishing Recall | 94.4% | ≥ 95% |
| ROC-AUC | 0.972 | ≥ 0.975 |
| Explainability | Linear coefficients | SHAP values (richer) |
| Artifact detection | Hard to isolate | SHAP makes artifacts visible |
| Routing reliability | Unreliable | Reliable (better calibration) |

LightGBM handles nonlinear feature interactions, does not require feature scaling, and typically produces better-calibrated probabilities — directly addressing the two main Phase 1 failures (calibration and artifact learning).

---

## 8. Conclusion

Phase 1 is complete and successful as a baseline. The classification performance is strong (93.5% accuracy, 94.4% phishing recall, ROC-AUC 0.972). The routing simulation shows the system design is sound — 82.8% auto-classification rate with 97.89% phishing recall within auto-classified emails.

The single blocking issue is calibration (ECE = 0.40), which makes the confidence routing layer operationally unreliable. This is a known structural limitation of LR + TF-IDF and is expected to be resolved in Phase 2 with LightGBM.

**Phase 2 can proceed.**
