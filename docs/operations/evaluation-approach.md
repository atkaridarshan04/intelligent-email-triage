# Evaluation Approach

## Overview

This document defines how the model's performance is measured, what success looks like for the v1 prototype, and how evaluation evolves as the system matures.

The evaluation approach must answer two questions:
1. Is the model classifying emails correctly?
2. Is the model actually reducing analyst workload?

Both matter. A model that is technically accurate but doesn't reduce false positives in practice has failed the core objective.

**Note on evaluation scope:** The model is trained and evaluated on two classes (Spam / Phishing). Analyst Review is an operational routing outcome, not a model class, and is evaluated separately under routing metrics.

---

## Evaluation Metrics

### Per-Class Metrics

For each of the two model classes (Spam, Phishing):

| Metric | Formula | Why It Matters |
|---|---|---|
| Precision | TP / (TP + FP) | Of emails classified as X, how many actually are X? |
| Recall | TP / (TP + FN) | Of all actual X emails, how many did we catch? |
| F1-Score | 2 × (P × R) / (P + R) | Harmonic mean — balances precision and recall |

### Overall Metrics

| Metric | Purpose |
|---|---|
| Macro F1 | Average F1 across both classes — treats each class equally |
| Weighted F1 | F1 weighted by class frequency — reflects real-world distribution |
| ROC-AUC | Discriminative ability regardless of threshold |
| Confusion Matrix | Full picture of which classes are being confused |

### Operational Metrics (Most Important for This Project)

| Metric | Definition | Target (v1) |
|---|---|---|
| Phishing Recall | % of actual phishing emails correctly identified | > 98% |
| Overall Accuracy | Correct classifications across both classes | > 95% |
| Phishing Precision | % of phishing-classified emails that are actually phishing | > 95% |
| False Positive Rate (phishing) | % of spam emails incorrectly classified as phishing | < 2% |
| AUC | Overall discriminative ability | > 0.97 |
| Analyst Queue Reduction | % reduction in emails requiring manual review vs. baseline | > 50% |
| Mean Inference Latency | End-to-end classification time | < 300ms |

**Phishing recall is the most critical metric.** Missing a real phishing email is worse than a false positive. The model should err on the side of flagging for review rather than auto-suppressing.

---

## Evaluation Dataset Setup

### Train / Validation / Test Split

- **Training set:** 70% — used for model training
- **Validation set:** 15% — used for hyperparameter tuning and threshold selection
- **Test set:** 15% — held out, never used during training or tuning, used only for final evaluation

All splits are **stratified** to maintain class proportions. Where timestamps are available, the test set should be temporally later than the training set.

### Cross-Dataset Evaluation

Train on one dataset combination, test on a different dataset. This measures generalization — whether the model works on emails it has never seen from a different source.

Example:
- Train on: SpamAssassin + Nazario + CEAS
- Test on: TREC 2007 + IWSPA-AP

Poor cross-dataset performance indicates overfitting to dataset-specific artifacts.

### Temporal Evaluation

Where datasets have timestamps, evaluate on chronologically later emails after training on earlier ones. This simulates real-world deployment where the model must handle new emails it hasn't seen.

---

## Baseline Comparison

The model must be compared against a baseline to demonstrate value.

### Baseline: Rule-Based Classifier

A simple rule-based system using:
- Known spam keyword list
- URL pattern matching (suspicious TLDs, IP literal URLs)
- Sender structure rules (reply-to mismatch, free-email sender)

This represents the "current state" of basic automated filtering. The model should outperform this baseline on phishing recall and analyst workload reduction.

---

## Confidence Calibration Evaluation

A well-calibrated model means: when it says 80% confidence, it should be correct ~80% of the time.

Evaluate calibration using:
- **Reliability diagram (calibration curve):** Plot predicted confidence vs. actual accuracy
- **Expected Calibration Error (ECE):** Quantifies miscalibration. Target: ECE < 0.05 after temperature scaling.

Poor calibration means the Analyst Review threshold is unreliable.

---

## Analyst Review Routing Evaluation

The Analyst Review routing is evaluated separately:

| Metric | Definition |
|---|---|
| Routing Precision | Of emails routed to Analyst Review, what % actually needed review? |
| Routing Recall | Of emails that needed review, what % were correctly routed? |
| Routing Rate | What % of all emails are routed to Analyst Review? |

Target: routing rate ≤ 30% of all reported emails at v1. Should decrease over time as the model improves through the feedback loop.

---

## Evaluation Against Analyst Verdicts (Post-Deployment)

Once the system is deployed and analysts are providing feedback:

- Compare model predictions against analyst verdicts on the same emails
- Track override rate over time (should decrease as model improves)
- Identify systematic errors: which email types is the model consistently wrong about?

This is the most realistic evaluation because it uses real emails from the actual deployment environment.

---

## Evaluation Reporting

Each evaluation run produces a report containing:

1. Confusion matrix (absolute counts and percentages)
2. Per-class precision, recall, F1
3. Overall macro and weighted F1
4. ROC-AUC
5. Calibration curve and ECE
6. Analyst Review routing metrics
7. Comparison against baseline
8. Cross-dataset generalization results (if applicable)
9. Notable failure cases (examples of misclassified emails with analysis)

Reports are versioned and stored alongside model checkpoints for traceability.

---

## Evaluation Schedule

| Phase | Evaluation Type |
|---|---|
| During development | Validation set metrics after each training run |
| Before v1 release | Full test set evaluation + baseline comparison |
| Post-deployment (monthly) | Analyst verdict comparison + override rate tracking |
| At each retraining | Full test set re-evaluation + comparison to previous model version |
