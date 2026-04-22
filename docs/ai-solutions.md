# AI System Design: Spam, Junk, and Phishing Email Classification

## 1. Scope and Objective

This document covers the AI design for a system that classifies user-reported emails into four categories:

- **Spam** — unsolicited bulk, non-malicious; auto-folder
- **Junk** — low-quality / suspicious nuisance; junk route
- **Phishing** — credential theft, fraud, malware, impersonation; immediate alert
- **Analyst Review** — low-confidence or conflicting indicators; manual triage

The system produces a calibrated 0–100 risk score and machine-readable reasoning for every decision.

---

## 2. Problem Framing

From an AI perspective, this is a **risk-sensitive multi-class classification problem under ambiguity**.

Key characteristics:

- **Class overlap:** Spam and phishing share linguistic and structural features
- **Class imbalance:** Phishing samples are significantly fewer than spam and junk
- **Concept drift:** Attack patterns evolve — models must adapt
- **Adversarial inputs:** Attackers deliberately craft emails to evade detection
- **Analyst Review is a first-class output:** Low-confidence cases are explicitly routed to analysts, not silently misclassified

The system must learn **contextual and semantic signals**, not just keywords, and must provide **calibrated confidence scores** with explainable reasoning.

---

## 3. Model Architecture

### Design Principle

A **single unified multimodal neural architecture** rather than multiple disconnected classifiers. All signal types — text, metadata, and behavioral — are fused into one trainable model.

### Architecture Overview

```
Text Inputs     → Transformer Encoder  ─┐
Metadata Inputs → Dense Encoder (MLP)  ─┼─→ Fusion Layer → Classification Head
Behavior Inputs → Dense Encoder (MLP)  ─┘
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

Softmax output across four classes: Spam, Junk, Phishing, Analyst Review.

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
- Homograph detection (Unicode lookalike characters)
- Redirect chain depth
- Domain age and registration recency
- Mismatch between display text and actual URL

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
  "confidence": 0.95,
  "risk_score": 0-100,
  "reasons": [
    "Credential request language detected",
    "Unknown sender domain",
    "SPF authentication failed",
    "Suspicious redirect URL"
  ]
}
```

Routing logic based on output:

| Output Condition | Action |
|---|---|
| High confidence Spam | Auto-folder |
| High confidence Junk | Junk route |
| High confidence Phishing | Immediate alert |
| Low confidence (any class) | Analyst Review queue |

---

## 6. Decision Logic and Confidence Thresholding

| Confidence Range | Interpretation |
|---|---|
| 0.85 – 1.00 | High confidence — auto-classify |
| 0.70 – 0.84 | Moderate confidence — classify with note |
| 0.50 – 0.69 | Low confidence — Analyst Review |
| < 0.50 | Very low confidence — always Analyst Review |

Risk score (0–100) is derived from calibrated model probabilities using Platt scaling.

---

## 7. Explainability

Each inference returns machine-readable reasons using:

- **Attention token attribution** — which text tokens drove the classification
- **SHAP** — feature importance for metadata inputs
- **Rule summarization layer** — human-readable signal descriptions

---

## 8. Training Data Strategy

All training data must come from **publicly available datasets**. See `datasets.md` for the full list.

Key considerations:
- Combine multiple datasets to improve coverage across all four classes
- Apply class balancing (oversample phishing, undersample spam) to address imbalance
- Use weighted multi-class cross entropy with higher penalty for phishing false negatives
- Hold out a test set that is never used during training or hyperparameter tuning

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
- Target inference latency: < 300ms

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
