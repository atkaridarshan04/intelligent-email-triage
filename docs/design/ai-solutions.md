# AI System Design: Spam and Phishing Email Classification

## 1. Scope and Objective

This document covers the AI design for a system that classifies user-reported suspicious emails and routes them to one of three operational outcomes:

- **Spam** — unsolicited bulk, non-malicious; auto-suppress
- **Phishing** — credential theft, fraud, malware, impersonation; immediate escalation
- **Analyst Review** — low-confidence prediction; manual triage

The model is trained on **two semantic classes** (Spam, Phishing). The third outcome — Analyst Review — is not a training label. It is an **operational routing state** triggered at inference time when the model's confidence is insufficient to automate a decision.

---

## 2. Problem Framing

This is a **risk-sensitive binary classification problem with confidence-based routing**.

Key characteristics:

- **Class overlap:** Spam and phishing share linguistic and structural features
- **Class imbalance:** Phishing samples are fewer than spam in public datasets
- **Concept drift:** Attack patterns evolve — models must adapt
- **Adversarial inputs:** Attackers craft emails to evade detection
- **Analyst Review is an operational output, not a learned class:** Low-confidence cases are routed to analysts via confidence thresholding, not by training the model to predict "Review"

---

## 3. Model Architecture

### Design Principle

A **hybrid multimodal architecture** combining transformer-based semantic understanding with deterministic structured feature learning. Both modalities are fused into a single classifier.

### Architecture Overview

```
Text Inputs (subject + body)  →  RoBERTa Encoder  ─┐
Structured Features           →  Dense MLP         ─┴─→  Fusion Layer  →  Binary Classifier
                                                                               ↓
                                                                      Confidence Layer
                                                                      (Trust Score + routing)
                                                                               ↓
                                                               Spam / Phishing / Analyst Review
```

### Component Specification

**Text Encoder**

Fine-tuned RoBERTa over email subject and body text.

Signals learned: urgency language, credential request intent, brand impersonation cues, financial pressure language, social engineering semantics.

Output: contextual dense embedding.

**Structured Feature Encoder**

Multi-layer perceptron (MLP) over deterministically extracted features:

| Feature Group | Features |
|---|---|
| Sender | Display/From mismatch, reply-to mismatch, free-email sender |
| URLs | URL count, domain count, shortened URL presence, suspicious TLD, IP literal URL, URL entropy, typosquatting similarity |
| Attachments | Attachment presence, archive detection, executable detection, macro-enabled document detection |
| Text statistics | Subject length, body length, uppercase ratio, digit ratio, punctuation density, link density |
| Brand | Known brand mention, sender-brand mismatch |

All features are deterministically derivable from email content without relying on enterprise telemetry.

**Fusion Layer**

Concatenation of transformer embedding and structured feature vector, passed to the classification head.

**Classification Head**

Binary output: Spam probability / Phishing probability.

**Confidence Routing Layer**

Post-inference confidence mechanism determines whether automation is safe. Low-confidence predictions are escalated to Analyst Review rather than forced into an incorrect automated decision.

---

## 4. Why This Architecture

**Practical dataset reality:** Public datasets are heterogeneous and often incomplete. The architecture avoids dependence on unavailable enterprise telemetry (SPF/DKIM/DMARC, IP reputation, sender history).

**Strong generalization:** The transformer learns semantic attack patterns. Structured features provide complementary infrastructure signals. This reduces over-reliance on either modality alone.

**Operational explainability:** Structured features improve interpretability. Analysts can understand signals such as suspicious sender mismatch, risky URL structure, and malicious attachment indicators — not just opaque text classification.

**Security safety:** No LLM-based reasoning is used in the classification pipeline. This avoids prompt injection risks, non-deterministic inference behavior, and security policy ambiguity.

---

## 5. Classification Output

Every email processed by the system produces:

```json
{
  "label": "Spam" | "Phishing" | "Analyst Review",
  "spam_probability": 0.04,
  "phishing_probability": 0.93,
  "trust_score": 91,
  "reasons": [
    "Credential request language detected",
    "Reply-to mismatch detected",
    "Sender domain newly observed",
    "Suspicious URL structure"
  ],
  "confidence_notes": [
    "Strong class separation (margin: 0.89)"
  ]
}
```

Routing logic:

| Output Condition | Action |
|---|---|
| High-confidence Spam | Auto-suppress |
| High-confidence Phishing | Immediate escalation |
| Low confidence (either class) | Analyst Review queue |

---

## 6. Confidence Layer

The model outputs probabilities for two classes. These pass through a **Confidence Layer** that computes a composite Trust Score before any routing decision is made.

### Trust Score

```
trust_score = w1 * max_prob + w2 * margin_score
```

- **max_prob** — highest class probability from the calibrated output
- **margin_score** — difference between the two class probabilities (catches ambiguity max probability misses)

Normalized to 0–100. Default weights: `w1=0.6, w2=0.4`.

Raw probabilities are calibrated via temperature scaling before trust score computation.

### Routing Table

| Trust Score | Routing Decision |
|---|---|
| > 90 | Auto-classify |
| 75 – 90 | Auto-classify with monitoring flag |
| 55 – 75 | Analyst Review queue |
| < 55 | Priority Analyst Review |

### Security Override

If phishing probability exceeds 0.70 and any high-weight malicious signal is present, the email is escalated immediately regardless of trust score.

See `confidence-and-explainability.md` for the full specification.

---

## 7. Explainability

Every inference produces two explanation outputs: **why this class** and **why this confidence level**.

**Structured feature importance (SHAP on MLP):** Delivered inline with the routing decision. Fast, deterministic, derived from features already extracted during inference.

Examples: `reply-to mismatch`, `suspicious URL count: 3`, `sender domain age: 2 days`

**Text attribution (Integrated Gradients → rule summarizer):** Delivered async to the analyst interface after routing. Token-level attribution from the transformer feeds a rule summarizer that maps contributions to phrase-level sentence templates.

Examples: `"Credential request language detected"`, `"Urgency combined with account reference"`, `"Brand impersonation pattern in subject"`

This two-tier split is required to meet the inline latency target. Analysts receive the routing decision immediately; deep attribution is available when they open the review queue.

See `confidence-and-explainability.md` for the full specification.

---

## 8. Training Data Strategy

All training data comes from **publicly available datasets**. See `docs/research/datasets.md` for the full list and `docs/implementation/dataset-plan.md` for construction details.

Key considerations:

- The model is trained on **two classes only**: Spam and Phishing
- Analyst Review is not a training label — it is derived at inference time from confidence thresholds
- Dataset composition is stratified by era, source diversity, and phishing subtype — not only by raw sample count
- Weighted binary cross-entropy with higher penalty for phishing false negatives
- Test set is held out and never used during training or hyperparameter tuning
- A **sampling manifest** is generated at dataset construction time, recording source, era bucket, attack subtype, and label for every training sample

---

## 9. Feedback Loop Integration

Analyst verdicts feed back into the model to improve accuracy over time. See `docs/operations/feedback-loop.md` for the full design.

---

## 10. Deployment Stack

- Python inference service (PyTorch)
- FastAPI REST API
- Containerized deployment (Docker)
- Target inline inference latency: < 300ms

### Two-Tier Pipeline

**Tier 1 — Inline (<300ms):**
Email parsing → feature extraction → model inference → temperature scaling → trust score → security override check → routing decision → rule-based reasons

**Tier 2 — Async (post-routing):**
Integrated Gradients text attribution → SHAP metadata explanation → results pushed to analyst interface
