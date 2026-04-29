# Confidence Layer and Explainability Framework

## Overview

The classifier outputs probabilities for three classes (Spam, Junk, Phishing). Before any routing decision is made, those probabilities pass through two post-inference layers:

1. **Confidence Layer** — computes a composite Trust Score and determines whether to automate or escalate
2. **Explainability Layer** — produces human-readable evidence for the decision and the confidence level

We separate prediction confidence from classification itself. This prevents over-automation, enables intelligent escalation, and provides transparent analyst reasoning.

```
3-Class Model Output (Spam / Junk / Phishing probabilities)
    ↓
Confidence Layer  →  Trust Score (0–100) + routing decision
    ↓
Explainability Layer  →  reasons[] + confidence_notes[]
    ↓
Final Output: label + trust_score + reasons + confidence_notes
```

---

## 1. Confidence Layer

### Three-Signal Stack

A single softmax max probability is insufficient for reliable routing. The confidence layer combines three signals:

**Signal A — Max Probability**

The highest class probability from the softmax output.

```
Spam=0.92, Junk=0.05, Phishing=0.03  →  max_prob = 0.92
```

Useful but overconfident on its own. Raw softmax probabilities are not calibrated — a model can output 0.92 on an out-of-distribution input.

**Signal B — Margin Score**

Difference between the top two class probabilities.

```
Spam=0.51, Junk=0.47, Phishing=0.02  →  margin = 0.51 - 0.47 = 0.04
```

A high max probability with a low margin means the model is nearly split between two classes — the prediction is unreliable regardless of the top value. Margin catches ambiguity that max probability misses.

**Signal C — Novelty Score (OOD Risk)**

Deferred to v2. See Trust Score Formula below for rationale.

### Trust Score Formula

```
trust_score = w1 * max_prob + w2 * margin_score
```

Normalized to 0–100. Default weights: `w1=0.6, w2=0.4`.

Weights are tunable post-deployment based on analyst correction patterns.

**OOD detection deferred to v2.** A novelty score (embedding distance from training distribution) was evaluated for v1 but removed. Centroid-based cosine distance over transformer embeddings produces false-OOD signals on stylistically unusual but legitimate emails — formal legal language, technical jargon, non-standard formatting — inflating the Analyst Review rate without improving safety. Transformer embeddings do not form spherical clusters, making cosine distance to a single centroid per class unreliable. v2 will introduce Mahalanobis distance over per-class embedding distributions, or a dedicated learned reject head, once the deployment baseline is established.

### Calibration (Temperature Scaling)

Raw softmax probabilities are systematically overconfident. Before computing the trust score, logits are scaled by a learned temperature parameter `T`:

```
calibrated_prob = softmax(logits / T)
```

`T` is fit on the validation set after training (not during training). This is the standard industry practice for probability calibration. Expected Calibration Error (ECE) is measured before and after to confirm improvement.

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

Even at medium trust, if phishing probability is high and strong malicious indicators are present, the email is escalated immediately regardless of trust score:

```python
if phishing_prob > 0.70 and high_weight_signal_present:
    return "Phishing", escalate=True
```

High-weight signals that trigger this override: credential request in body, SPF+DKIM both failing, lookalike/homograph domain, known malicious URL, BEC pattern (executive impersonation + financial request), executable or macro-enabled attachment.

### Worked Examples

| Spam | Junk | Phishing | Trust | Output |
|---|---|---|---|---|
| 0.92 | 0.05 | 0.03 | High | Spam (auto) |
| 0.04 | 0.03 | 0.93 | High | Phishing (immediate alert) |
| 0.51 | 0.47 | 0.02 | Low (margin=0.04) | Analyst Review |
| 0.43 | 0.41 | 0.16 | Low | Analyst Review |
| 0.30 | 0.25 | 0.45 | Low + override check | Phishing if override triggers, else Review |

---

## 3. Explainability Layer

Every decision produces two explanation outputs: **why this class** and **why this confidence level**.

The explainability pipeline is split across two tiers to meet the inline latency target.

**Tier 1 — Inline:** Rule summarizer reasons + SHAP on metadata MLP. Delivered with the routing decision.

**Tier 2 — Async:** Integrated Gradients on the transformer encoder. Delivered to the analyst interface after routing.

### Attribution Sources

**Text Attribution (Integrated Gradients → Rule Summarizer)**

Integrated Gradients identifies which tokens in the subject and body most influenced the classification. Raw token-level scores are not surfaced directly — they feed the rule summarizer, which maps token contributions to phrase-level sentence templates. This produces actionable analyst-facing reasons rather than raw salience lists.

Examples of rule summarizer output: `"Credential request language detected"`, `"Urgency combined with account reference"`, `"Brand impersonation pattern in subject"`

**Metadata Importance (SHAP on MLP)**

SHAP is applied to the metadata MLP encoder only — the correct tool for tabular features. It is not applied to the transformer text encoder.

Examples: `SPF failed`, `newly registered sender domain`, `reply-to mismatch`, `suspicious URL count: 3`

**Behavioral Reasoning (Rule Summarizer)**

Human-readable descriptions of anomaly signals from the behavioral encoder.

Examples: `sender unseen historically`, `abnormal send hour (3:14 AM)`, `similar emails sent to multiple users`

### Rule Summarizer

The rule summarizer converts raw feature contributions into natural-language sentences. It is a deterministic template layer — it maps feature names and values to pre-defined sentence templates. This keeps explanations consistent, auditable, and reproducible across model versions.

---

## 4. Output Schemas

### Auto-Classified Output

```json
{
  "label": "Phishing",
  "confidence": 0.93,
  "trust_score": 91,
  "risk_score": 88,
  "reasons": [
    "Credential request language detected",
    "SPF authentication failed",
    "Sender domain newly observed (< 30 days)",
    "Embedded URL resembles known brand spoofing"
  ],
  "confidence_notes": [
    "Strong class separation (margin: 0.89)",
    "Pattern similar to known phishing training samples"
  ]
}
```

### Analyst Review Output

```json
{
  "label": "Analyst Review",
  "predicted_class": "Junk",
  "confidence": 0.51,
  "trust_score": 58,
  "risk_score": 44,
  "reasons": [
    "Low sender reputation score",
    "Promotional language detected"
  ],
  "confidence_notes": [
    "Spam and Junk probabilities too close (margin: 0.04)"
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
