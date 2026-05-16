# Confidence Layer and Explainability Framework

## Overview

The classifier outputs probabilities for two classes (Spam / Phishing). Before any routing decision is made, those probabilities pass through two post-inference layers:

1. **Confidence Layer** — computes a composite Trust Score and determines whether to automate or escalate
2. **Explainability Layer** — produces human-readable evidence for the decision and the confidence level

```
Binary Model Output (Spam / Phishing probabilities)
    ↓
Confidence Layer  →  Trust Score (0–100) + routing decision
    ↓
Explainability Layer  →  reasons[] + confidence_notes[]
    ↓
Final Output: label + trust_score + reasons + confidence_notes
```

---

## 1. Confidence Layer

### Two-Signal Stack

A single max probability is insufficient for reliable routing. The confidence layer combines two signals:

**Signal A — Max Probability**

The highest class probability from the calibrated output.

```
Spam=0.92, Phishing=0.08  →  max_prob = 0.92
```

Useful but overconfident on its own. Raw probabilities are not calibrated — a model can output 0.92 on an out-of-distribution input.

**Signal B — Margin Score**

Difference between the two class probabilities.

```
Spam=0.53, Phishing=0.47  →  margin = 0.53 - 0.47 = 0.06
```

A high max probability with a low margin means the model is nearly split — the prediction is unreliable regardless of the top value. Margin catches ambiguity that max probability misses.

### Trust Score Formula

```
trust_score = w1 * max_prob + w2 * margin_score
```

Normalized to 0–100. Default weights: `w1=0.6, w2=0.4`.

Weights are tunable post-deployment based on analyst correction patterns.

### Calibration (Temperature Scaling)

Raw probabilities are systematically overconfident. Before computing the trust score, logits are scaled by a learned temperature parameter `T`:

```
calibrated_prob = softmax(logits / T)
```

`T` is fit on the validation set after training. Expected Calibration Error (ECE) is measured before and after to confirm improvement. Target: ECE < 0.05 after temperature scaling.

---

## 2. Routing Logic

### Primary Routing Table

| Trust Score | Routing Decision |
|---|---|
| > 90 | Auto-classify |
| 75 – 90 | Auto-classify with low-priority monitoring flag |
| 55 – 75 | Analyst Review queue |
| < 55 | Priority Analyst Review |

### Security Override Rule

Even at medium trust, if phishing probability is high and strong malicious indicators are present, the email is escalated immediately:

```python
if phishing_prob > 0.70 and high_weight_signal_present:
    return "Phishing", escalate=True
```

High-weight signals that trigger this override: credential request in body, lookalike/typosquatting domain, BEC pattern (executive impersonation + financial request), executable or macro-enabled attachment, IP address as URL host.

### Worked Examples

| Spam | Phishing | Trust | Output |
|---|---|---|---|
| 0.92 | 0.08 | High | Spam (auto-suppress) |
| 0.04 | 0.96 | High | Phishing (immediate escalation) |
| 0.53 | 0.47 | Low (margin=0.06) | Analyst Review |
| 0.30 | 0.70 | Override check | Phishing if override triggers, else Review |

---

## 3. Explainability Layer

Every decision produces two explanation outputs: **why this class** and **why this confidence level**.

The explainability pipeline is split across two tiers to meet the inline latency target.

**Tier 1 — Inline:** Rule summarizer reasons + SHAP on structured feature MLP. Delivered with the routing decision.

**Tier 2 — Async:** Integrated Gradients on the transformer encoder. Delivered to the analyst interface after routing.

### Attribution Sources

**Structured Feature Importance (SHAP on MLP)**

SHAP is applied to the structured feature MLP encoder. Fast, deterministic, delivered inline.

Examples: `reply-to mismatch`, `sender domain age: 2 days`, `suspicious URL count: 3`, `free-email sender impersonating brand`

**Text Attribution (Integrated Gradients → Rule Summarizer)**

Integrated Gradients identifies which tokens most influenced the classification. Raw token-level scores feed the rule summarizer, which maps contributions to phrase-level sentence templates. This produces actionable analyst-facing reasons rather than raw salience lists.

Examples: `"Credential request language detected"`, `"Urgency combined with account reference"`, `"Brand impersonation pattern in subject"`

### Rule Summarizer

The rule summarizer converts raw feature contributions into natural-language sentences. It is a deterministic template layer — it maps feature names and values to pre-defined sentence templates. This keeps explanations consistent, auditable, and reproducible across model versions.

---

## 4. Output Schemas

### Auto-Classified Output

```json
{
  "label": "Phishing",
  "spam_probability": 0.04,
  "phishing_probability": 0.93,
  "trust_score": 91,
  "reasons": [
    "Credential request language detected",
    "Reply-to mismatch detected",
    "Sender domain newly observed (< 30 days)",
    "Suspicious URL structure with high entropy"
  ],
  "confidence_notes": [
    "Strong class separation (margin: 0.89)"
  ]
}
```

### Analyst Review Output

```json
{
  "label": "Analyst Review",
  "predicted_class": "Phishing",
  "spam_probability": 0.47,
  "phishing_probability": 0.53,
  "trust_score": 58,
  "reasons": [
    "Urgency language detected",
    "Free-email sender"
  ],
  "confidence_notes": [
    "Spam and Phishing probabilities too close (margin: 0.06)"
  ]
}
```

The `predicted_class` field in Review outputs tells the analyst what the model's best guess was, even though confidence was insufficient to automate.

---

## 5. Confidence Evaluation

Calibration quality is measured using:

- **Reliability diagram** — plots predicted confidence vs. actual accuracy in bucketed ranges. A well-calibrated model produces a diagonal line.
- **Expected Calibration Error (ECE)** — quantifies average miscalibration. Target: ECE < 0.05 after temperature scaling.

Routing threshold performance is evaluated separately:

| Metric | Definition |
|---|---|
| Routing Precision | Of emails routed to Analyst Review, what % actually needed review? |
| Routing Recall | Of emails that needed review, what % were correctly routed? |
| Routing Rate | % of all emails routed to Analyst Review (target: ≤ 30% at v1) |

Thresholds are recalibrated periodically based on analyst correction patterns from the feedback loop.
