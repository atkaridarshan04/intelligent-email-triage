# AI System Design: Spam, Junk, and Phishing Email Classification

## 1. Scope and Objective

This document covers the AI design for a system that classifies user-reported emails and routes them to one of four operational outcomes:

- **Spam** — unsolicited bulk, non-malicious; auto-folder
- **Junk** — low-quality / suspicious nuisance; junk route
- **Phishing** — credential theft, fraud, malware, impersonation; immediate alert
- **Analyst Review** — low-confidence or conflicting indicators; manual triage

The model is trained on **three semantic classes** (Spam, Junk, Phishing). The fourth outcome — Analyst Review — is not a training label. It is an **operational routing state** triggered at inference time when the model's confidence is insufficient to automate a decision. See Section 6 for the full threshold logic.

The system produces a calibrated 0–100 risk score and machine-readable reasoning for every decision.

---

## 2. Problem Framing

From an AI perspective, this is a **risk-sensitive 3-class classification problem with uncertainty-driven routing**.

Key characteristics:

- **Class overlap:** Spam and phishing share linguistic and structural features
- **Class imbalance:** Phishing samples are significantly fewer than spam and junk
- **Concept drift:** Attack patterns evolve — models must adapt
- **Adversarial inputs:** Attackers deliberately craft emails to evade detection
- **Analyst Review is an operational output, not a learned class:** Low-confidence cases are explicitly routed to analysts via confidence thresholding, not by training the model to predict "Review"

The system must learn **contextual and semantic signals**, not just keywords, and must provide **calibrated confidence scores** with explainable reasoning.

---

## 3. Model Architecture

### Design Principle

A **single unified multimodal neural architecture** rather than multiple disconnected classifiers. All signal types — text, metadata, and behavioral — are fused into one trainable model.

### Architecture Overview

```
Text Inputs     → Transformer Encoder  ─┐
Metadata Inputs → Dense Encoder (MLP)  ─┼─→ Fusion Layer → Classification Head (3-class softmax)
Behavior Inputs → Dense Encoder (MLP)  ─┘                        ↓
                                                         Confidence Layer
                                                         (Trust Score + routing)
                                                                  ↓
                                                         Explainability Layer
                                                         (reasons + confidence_notes)
                                                                  ↓
                                                    Spam / Junk / Phishing / Analyst Review
```

### Component Specification

**Text Encoder**

Fine-tuned transformer over subject, body, sender display text, and URL token text.

Recommended model: **RoBERTa** (primary), DeBERTa, or DistilBERT (latency-optimized).

Signals learned: urgency language, credential request intent, brand impersonation cues, financial pressure language, social engineering semantics.

Output: contextual dense embedding.

**Metadata Encoder**

Multi-layer perceptron (MLP) over normalized structured features:

| Feature | Feature |
|---|---|
| SPF result | DKIM result |
| DMARC result | Number of links |
| Number of attachments | Domain age |
| TLD risk score | Reply-to mismatch |
| HTML/text ratio | Sender reputation score |

**Behavioral Encoder**

MLP over anomaly and trust signals:

| Feature | Feature |
|---|---|
| Sender seen before | Historical sender trust |
| Communication frequency | Typical send hour deviation |
| First-time domain indicator | Similar campaign burst score |
| Department targeting anomaly | |

**Fusion Layer**

Concatenation + gated attention weighting across all three encoder outputs.

**Classification Head**

Softmax output across three classes: Spam, Junk, Phishing.

Analyst Review is not a model output class. It is determined post-inference by the confidence thresholding layer described in Section 6.

---

## 4. Feature Design

### 4.1 Email Content Features
- Subject line and body text (transformer embeddings)
- Urgency indicators: "act now", "verify your account", "limited time"
- Impersonation signals: executive names, brand names, IT/HR context
- Credential request patterns: "enter your password", "confirm your details"
- Tone analysis: threatening, authoritative, alarming

### 4.2 URL and Link Features
- Number of URLs in email
- URL structure: domain, TLD, path depth, query parameters
- Homograph detection (Unicode lookalike characters — requires Unicode normalization pass, not only edit distance)
- Domain age and registration recency
- Mismatch between display text and actual URL
- Suspicious TLD patterns (.xyz, .top, .tk, .ml, .ga, .click)
- IP address as URL host, port number in URL
- URL shortener presence (flagged as signal; not expanded inline)
- PhishTank/SURBL lookup against locally cached threat intel feed (updated hourly; no live outbound calls at inference time)

**URL redirect chain following is not performed inline.** Live outbound HTTP requests to attacker-controlled URLs introduce SSRF risk and make the <300ms latency target unachievable. Redirect expansion, if required, runs in an isolated async enrichment sandbox after routing and delivers results to the analyst interface separately.

### 4.3 Sender and Infrastructure Features
- SPF result (pass / fail / softfail / none)
- DKIM result (pass / fail / none)
- DMARC result and policy
- Sender domain age
- IP reputation (cross-referenced against public threat intel feeds)
- Reply-to vs. From mismatch
- Sending volume anomalies

### 4.4 Sender–Recipient Relationship Features
- First-contact detection (has this sender emailed this recipient before?)
- Historical communication frequency
- Domain familiarity (is the sender domain known to the organization?)

### 4.5 Behavioral and Metadata Features
- Time of send (off-hours, weekends)
- Header routing anomalies
- Attachment presence and type
- HTML-to-text ratio (heavily HTML with minimal text is a signal)

---

## 5. Classification Output

Every email processed by the system produces:

```json
{
  "label": "Spam" | "Junk" | "Phishing" | "Analyst Review",
  "confidence": 0.93,
  "trust_score": 91,
  "risk_score": 88,
  "reasons": [
    "Credential request language detected",
    "SPF authentication failed",
    "Sender domain newly observed",
    "Suspicious redirect URL"
  ],
  "confidence_notes": [
    "Strong class separation (margin: 0.89)",
    "Pattern similar to known phishing training samples"
  ]
}
```

**Important:** The model is trained on three classes (Spam, Junk, Phishing). The label "Analyst Review" is assigned at inference time by the Confidence Layer when the Trust Score is insufficient to automate a decision. See Section 6 and `confidence-and-explainability.md` for routing logic.

Routing logic based on output:

| Output Condition | Action |
|---|---|
| High confidence Spam | Auto-folder |
| High confidence Junk | Junk route |
| High confidence Phishing | Immediate alert |
| Low confidence (any class) | Analyst Review queue |

---

## 6. Decision Logic and Confidence Layer

The model outputs probabilities for three classes: Spam, Junk, Phishing. These pass through a **Confidence Layer** that computes a composite Trust Score before any routing decision is made.

### Trust Score

Two signals are combined in v1:

- **Max probability** — highest class probability from the calibrated softmax
- **Margin score** — difference between top two class probabilities (catches ambiguity max probability misses)

```
trust_score = w1 * max_prob + w2 * margin_score
```

Normalized to 0–100. Default weights: `w1=0.6, w2=0.4`.

**Note on OOD detection:** A novelty score (embedding distance from training distribution) was considered for v1 but deferred. Centroid-based cosine distance produces noisy false-OOD signals on stylistically unusual but legitimate emails (formal legal language, technical jargon, non-standard formatting). This degrades analyst trust without improving safety. OOD detection will be introduced in v2 using Mahalanobis distance over per-class embedding distributions.

### Calibration

Raw softmax probabilities are overconfident. Temperature scaling is applied post-training on the validation set to produce calibrated probabilities before trust score computation.

### Routing Table

| Trust Score | Routing Decision |
|---|---|
| > 90 | Auto-classify |
| 75 – 90 | Auto-classify with low-priority monitoring flag |
| 55 – 75 | Analyst Review queue |
| < 55 | Priority Analyst Review |

### Security Override

If phishing probability exceeds 0.70 and any high-weight malicious signal is present, the email is escalated immediately regardless of trust score.

See `confidence-and-explainability.md` for the full specification including worked examples, weight tuning, and calibration evaluation.

---

## 7. Explainability

Every inference produces two explanation outputs: **why this class** and **why this confidence level**.

The pipeline is split into two tiers to meet the <300ms inline latency target:

**Tier 1 — Inline (delivered with routing decision):**
- Rule-based reasons from the rule summarizer — deterministic, fast, derived from signal extraction already performed during inference
- Metadata importance (SHAP on the metadata MLP) — structured feature contributions

**Tier 2 — Async (delivered to analyst interface after routing):**
- Text attribution (Integrated Gradients on the transformer encoder) — token-level attribution fed into the rule summarizer to produce phrase-level reasoning; not surfaced as raw token scores
- URL threat intel enrichment — PhishTank/SURBL cache lookup results

**Why this split:** SHAP on a transformer requires hundreds of masked forward passes and cannot meet the inline latency budget. Integrated Gradients on RoBERTa is similarly expensive. Analysts need routing decisions immediately; they need deep attribution when they open the review queue, not before. Async delivery is operationally correct.

**Attribution note:** Integrated Gradients output is token-level salience. Raw token scores (`"urgent"`, `"verify"`) are too granular to be actionable for analysts. IG output feeds the rule summarizer, which maps token contributions to phrase-level sentence templates. The rule summarizer output is what analysts see — consistent, auditable, and actionable.

Three attribution sources:

- **Text attribution (Integrated Gradients → rule summarizer)** — phrase-level reasons derived from transformer token salience (e.g., `"Credential request language detected"`, `"Urgency combined with account reference"`)
- **Metadata importance (SHAP on MLP)** — structured feature contributions (e.g., `SPF failed`, `reply-to mismatch`, `newly registered domain`)
- **Behavioral reasoning (rule summarizer)** — anomaly signals from the behavioral encoder (e.g., `sender unseen historically`, `abnormal send hour`)

Output schema for auto-classified emails:

```json
{
  "label": "Phishing",
  "confidence": 0.93,
  "trust_score": 91,
  "risk_score": 88,
  "reasons": ["Credential request language detected", "SPF authentication failed", "Sender domain newly observed", "Embedded URL resembles known brand spoofing"],
  "confidence_notes": ["Strong class separation (margin: 0.89)", "Pattern similar to known phishing training samples"]
}
```

Output schema for Analyst Review routing:

```json
{
  "label": "Analyst Review",
  "predicted_class": "Junk",
  "confidence": 0.51,
  "trust_score": 58,
  "risk_score": 44,
  "reasons": ["Low sender reputation score", "Promotional language detected"],
  "confidence_notes": ["Spam and Junk probabilities too close (margin: 0.04)"]
}
```

See `confidence-and-explainability.md` for the full specification.

---

## 8. Training Data Strategy

All training data must come from **publicly available datasets**. See `datasets.md` for the full list.

Key considerations:
- The model is trained on **three classes only**: Spam, Junk, Phishing
- "Analyst Review" is not a training label — it is derived at inference time from confidence thresholds
- Dataset composition is **class-balanced and stratified by time period, source diversity, and phishing subtype** — not only by raw sample count
- Apply class balancing (oversample phishing, undersample spam) to address imbalance
- Use weighted multi-class cross entropy with higher penalty for phishing false negatives
- Hold out a test set that is never used during training or hyperparameter tuning
- A **sampling manifest** is generated at dataset construction time, recording source, era bucket, attack subtype, and label for every training sample. This manifest is versioned alongside the model checkpoint for full reproducibility and audit traceability.

---

## 9. Feedback Loop Integration

Analyst verdicts feed back into the model to improve accuracy over time. See `feedback-loop.md` for the full design.

At the AI level:
- Analyst-corrected labels are stored with the original email features
- Periodic retraining incorporates new labeled data
- Confidence thresholds are recalibrated based on analyst correction patterns
- High-correction-rate categories trigger targeted data collection

---

## 10. Handling Hard Cases

### BEC (Business Email Compromise)
- No links or attachments — purely text-based social engineering
- Detection relies on: executive name detection, urgency + financial context, sender–recipient anomaly, domain spoofing signals
- These will frequently route to Analyst Review in early versions — this is expected and correct behavior

### AI-Generated Phishing
- Perfect grammar, contextual tone — bypasses style-based heuristics
- Detection relies on: infrastructure signals, sender–recipient history, semantic intent patterns
- Hardest category — model accuracy here will improve most with analyst feedback

---

## 11. Deployment Stack

- Python inference service (PyTorch)
- FastAPI REST / gRPC API
- Containerized deployment (Docker)
- Horizontal autoscaling (Kubernetes)
- Target inline inference latency: < 300ms

### Two-Tier Pipeline

**Tier 1 — Inline (<300ms):**
Email parsing → feature extraction → model inference → temperature scaling → trust score (max_prob + margin) → security override check → routing decision → rule-based reasons

**Tier 2 — Async (post-routing):**
Integrated Gradients text attribution → SHAP metadata explanation → URL threat intel enrichment → results pushed to analyst interface

This split is required to meet the latency target. RoBERTa inference + SHAP + Integrated Gradients running synchronously exceeds 300ms. Analysts receive the routing decision immediately; deep attribution is available when they open the review queue.

---

## 12. Key Challenges

- **Class imbalance:** Phishing samples are rare — requires careful sampling and loss weighting
- **Concept drift:** Phishing tactics evolve — model must be retrained periodically
- **Adversarial inputs:** Attackers will probe and adapt — model must not rely on easily-gamed features
- **Explainability:** Analysts need to understand why an email was flagged — feature attribution is required
- **Data quality:** Public datasets may contain outdated or mislabeled samples — validation is critical

---

## 13. Future Directions (Out of Scope for v1)

- Multilingual detection
- Integration with M365, SIEM, or SOAR platforms
- Cross-channel correlation (email + SMS + voice)
- Graph-based campaign detection (linking related phishing emails by infrastructure)
- LLM-based reasoning for ambiguous case explanation

---

## 14. Conclusion

The chosen approach is a **RoBERTa-based multimodal fusion classifier** combining transformer text encoding, structured metadata encoding, and behavioral signal encoding into a single unified model. This provides the strongest balance of detection quality, maintainability, scalability, and operational realism. Accuracy improves iteratively through the analyst feedback loop and scheduled continual learning.
