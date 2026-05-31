# 05 — Metrics Explained

Every metric we report measures something different about the model's performance. This file explains each one from scratch.

## The Confusion Matrix — The Foundation of Everything

Before explaining any metric, you need to understand the confusion matrix. It's a 2×2 table showing what the model predicted vs what was actually true.

```
                    PREDICTED
                  Spam    Phishing
ACTUAL  Spam    [  TN  |   FP  ]
        Phishing[  FN  |   TP  ]
```

- **TP (True Positive):** Model said phishing, it IS phishing. ✅ Correct
- **TN (True Negative):** Model said spam, it IS spam. ✅ Correct
- **FP (False Positive):** Model said phishing, it's actually spam. ❌ Wrong (over-alert)
- **FN (False Negative):** Model said spam, it's actually phishing. ❌ Wrong (missed phishing — the worst outcome)

**In our project, FN is the most dangerous error.** A missed phishing email could lead to a data breach, financial loss, or malware infection.

---

## Accuracy

**Formula:** (TP + TN) / Total

**Plain English:** Out of all emails, what fraction did the model get right?

**Phase 2 result:** 97.62%

**What it means:** The model correctly classified 97.62% of all emails.

**Why it's not the primary metric:** Accuracy can be misleading. If 95% of emails were spam, a model that always predicts "spam" would have 95% accuracy — but it would miss every single phishing email. We care more about specific types of errors.

---

## Recall (also called Sensitivity or True Positive Rate)

**Formula:** TP / (TP + FN)

**Plain English:** Out of all actual phishing emails, what fraction did the model correctly identify as phishing?

**Phase 2 result:** 98.01% phishing recall

**What it means:** The model caught 98.01% of all phishing emails. It missed 1.99%.

**Why it's our PRIMARY metric:** Missing phishing is catastrophic. We want this as high as possible. The project target is >98%.

**The tradeoff:** Increasing recall usually decreases precision (you catch more phishing but also flag more spam as phishing). This is the fundamental tradeoff in classification.

---

## Precision

**Formula:** TP / (TP + FP)

**Plain English:** Out of all emails the model predicted as phishing, what fraction actually were phishing?

**Phase 2 result:** 97.55% phishing precision

**What it means:** When the model says "this is phishing", it's right 97.55% of the time.

**Why it matters:** Low precision means analysts get flooded with false alarms — spam emails incorrectly flagged as phishing. This wastes analyst time and erodes trust in the system.

---

## F1 Score

**Formula:** 2 × (Precision × Recall) / (Precision + Recall)

**Plain English:** The harmonic mean of precision and recall. A single number that balances both.

**Phase 2 result:** 0.9778 (phishing class)

**What it means:** A score between 0 and 1. Higher is better. 0.9778 is excellent.

**When to use it:** When you care about both precision and recall and want a single summary number.

---

## ROC-AUC (Area Under the ROC Curve)

**What is ROC?** The Receiver Operating Characteristic curve plots True Positive Rate (recall) vs False Positive Rate at every possible classification threshold.

**What is AUC?** The area under that curve. A perfect model has AUC = 1.0. A random model has AUC = 0.5.

**Phase 2 result:** 0.9959

**Plain English:** If you randomly pick one phishing email and one spam email, the model will rank the phishing email as more likely to be phishing 99.59% of the time.

**Why it matters:** ROC-AUC measures the model's ability to discriminate between classes regardless of the threshold you choose. It's a threshold-independent measure of quality.

---

## PR-AUC (Area Under the Precision-Recall Curve)

Similar to ROC-AUC but plots Precision vs Recall instead. More informative than ROC-AUC when classes are imbalanced.

**Phase 2 result:** 0.9959

**Why we prefer it:** Our dataset is slightly imbalanced (55% phishing, 45% spam). PR-AUC is more sensitive to performance on the minority class.

---

## Brier Score

**Formula:** Mean of (predicted_probability - actual_label)²

**Plain English:** How far off are the model's probability estimates from the true outcomes? Lower is better. 0 = perfect, 1 = worst possible.

**Phase 2 result:** 0.0207

**What it means:** The model's probability estimates are, on average, 0.0207 squared units away from the true outcome. This is very good.

**Important distinction:** Brier score measures the accuracy of probability values. ECE (below) measures whether those probabilities are well-calibrated. A model can have a good Brier score but still be miscalibrated.

---

## ECE (Expected Calibration Error)

This is the most complex metric. See `10-calibration-deep-dive.md` for a full explanation.

**Plain English:** If the model says "I'm 80% confident this is phishing", is it actually right 80% of the time? ECE measures how well the model's confidence scores match reality.

**Formula:** Weighted average of |accuracy - confidence| across probability bins.

**Phase 2 result:** 0.4455

**Target:** < 0.05

**What it means:** The model's confidence scores are severely overconfident. When it says "90% phishing", the actual accuracy in that confidence range is much lower (or higher) than 90%.

**Why it matters:** The routing system uses confidence scores to decide whether to auto-classify or send to analyst review. If confidence scores are wrong, the routing thresholds can't be trusted.

---

## Auto-Classification Rate

**Plain English:** What percentage of emails does the model handle automatically (without sending to an analyst)?

**Phase 2 result:** 96.8%

**What it means:** 96.8% of emails are auto-routed (either auto-suppressed as spam or auto-escalated as phishing). Only 3.2% go to analyst review.

**Why it matters:** This directly measures how much analyst workload the system reduces. The project goal is >50% reduction. 96.8% auto-classification far exceeds this.

---

## Phishing Recall Within Auto-Classified Emails

**Plain English:** Of the emails the model is confident enough to auto-classify, what fraction of phishing emails does it correctly identify?

**Phase 2 result:** 98.92%

**Why it matters:** This is the most operationally important metric. It tells you: of the emails the system handles automatically, how safe is it? 98.92% means the system is very safe for auto-classification.

---

## Summary Table

| Metric | Phase 1 (LR) | Phase 2 (LightGBM) | Target | Status |
|--------|-------------|---------------------|--------|--------|
| Accuracy | 93.51% | 97.62% | — | ✅ |
| Phishing Recall | 94.38% | **98.01%** | > 98% | ✅ |
| Phishing Precision | 93.56% | 97.55% | — | ✅ |
| ROC-AUC | 0.9720 | 0.9959 | — | ✅ |
| PR-AUC | 0.9687 | 0.9959 | — | ✅ |
| Brier Score | 0.0553 | 0.0207 | — | ✅ |
| ECE | 0.4043 | 0.4455 | < 0.05 | ❌ |
| Auto-classify rate | 82.8% | 96.8% | > 50% | ✅ |
| Ph. recall (auto) | 97.89% | 98.92% | — | ✅ |
