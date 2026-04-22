# AI System Design: Spam vs. Phishing Email Classification

## 1. Scope and Objective

This document covers the AI design for a system that classifies user-reported emails into three categories:

- **Spam / Junk** — low risk, no SOC action needed
- **Gray / Bulk** — ambiguous, minimal review needed
- **Phishing** — high risk, requires SOC investigation

The system must also produce a **confidence score** and a **"manual review required" flag** for borderline cases.

This is a prototype-first system. The initial goal is not perfection — a 40–50% reduction in false positives (spam/gray emails incorrectly escalated to analysts) is a meaningful success. Accuracy improves over time through analyst feedback.

---

## 2. Problem Framing

From an AI perspective, this is a **fine-grained, risk-sensitive, 3-class classification problem under ambiguity**.

Key characteristics:

- **Class overlap:** Spam and phishing share linguistic and structural features
- **Class imbalance:** Phishing samples are significantly fewer than spam and gray
- **Concept drift:** Attack patterns evolve — models must adapt
- **Adversarial inputs:** Attackers deliberately craft emails to evade detection
- **Gray zone:** Many emails don't cleanly fit spam or phishing — the gray bucket is a first-class output, not a fallback

The system must learn **contextual and semantic signals**, not just keywords, and must provide **calibrated confidence scores** rather than hard labels alone.

---

## 3. Recommended Model Approach

Given the prototype-first constraint and the need for explainability and iterative improvement, the recommended approach is a **staged architecture**:

### Stage 1: Feature-Based Baseline (Fast to build, interpretable)

A classical ML model (Random Forest or Gradient Boosting) trained on hand-crafted features:
- TF-IDF or bag-of-words on email body/subject
- Metadata features (SPF/DKIM/DMARC pass/fail, domain age, sender reputation)
- URL features (count, TLD, redirect depth, homograph detection)
- Header features (reply-to mismatch, X-Mailer, routing anomalies)

This gives a working baseline quickly and is easy to explain to stakeholders.

### Stage 2: Transformer-Based Semantic Model (Higher accuracy)

Fine-tune a pre-trained transformer (e.g., DistilBERT or RoBERTa) on email text for 3-class classification:
- Captures semantic intent (urgency, impersonation, credential requests)
- Handles subtle linguistic cues that keyword models miss
- Pre-trained on large corpora — requires less labeled data to fine-tune

### Stage 3: Ensemble Fusion (Production-ready)

Combine Stage 1 and Stage 2 outputs with URL-specific and metadata-specific sub-models:
- Weighted voting or a learned meta-classifier
- Confidence calibration (Platt scaling or temperature scaling)
- Low-confidence outputs trigger the "manual review" flag

This staged approach means the team can ship Stage 1 quickly, validate it with analysts, and progressively improve.

---

## 4. Feature Design

### 4.1 Email Content Features
- Subject line and body text (TF-IDF, embeddings)
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

```
{
  "classification": "spam" | "gray" | "phishing",
  "confidence": 0.0 – 1.0,
  "manual_review": true | false,
  "signals": {
    "top_features": [...],
    "url_risk": "low" | "medium" | "high",
    "auth_failures": ["spf_fail", "dkim_none"],
    "intent_signals": ["urgency", "credential_request"]
  }
}
```

The `manual_review` flag is set when:
- Confidence is below a configurable threshold (e.g., < 0.70)
- Classification is "gray" with any phishing-adjacent signals
- The model's top two classes are within a small margin of each other

---

## 6. Training Data Strategy

All training data must come from **publicly available datasets**. See `datasets.md` for the full list.

Key considerations:
- Combine multiple datasets to improve coverage across spam, gray, and phishing categories
- Apply class balancing (oversampling phishing, undersampling spam) to address imbalance
- Use focal loss during training to focus learning on hard/ambiguous examples
- Hold out a test set that is never used during training or hyperparameter tuning

---

## 7. Feedback Loop Integration

Analyst verdicts feed back into the model to improve accuracy over time. See `feedback-loop.md` for the full design.

At the AI level:
- Analyst-corrected labels are stored with the original email features
- Periodic retraining incorporates new labeled data
- Confidence thresholds are recalibrated based on analyst correction patterns
- High-correction-rate categories trigger targeted data collection

---

## 8. Handling Hard Cases

### BEC (Business Email Compromise)
- No links or attachments — purely text-based social engineering
- Detection relies on: executive name detection, urgency + financial context, sender–recipient anomaly, domain spoofing signals
- These will frequently trigger `manual_review: true` in early versions — this is expected and correct behavior

### AI-Generated Phishing
- Perfect grammar, contextual tone — bypasses style-based heuristics
- Detection relies on: infrastructure signals, sender–recipient history, semantic intent patterns
- Hardest category — model accuracy here will improve most with analyst feedback

### Gray Email Misclassification
- The most common source of false positives
- Gray emails with any phishing-adjacent signal (urgency, credential request, suspicious URL) should be flagged for review rather than auto-dismissed

---

## 9. Evaluation Methodology

See `evaluation-approach.md` for the full evaluation plan.

Key metrics:
- **Precision and Recall per class** — especially recall for phishing (missing a phishing email is worse than a false positive)
- **F1-score** — harmonic mean, useful for imbalanced classes
- **False Positive Rate for phishing** — directly measures analyst workload reduction
- **Confusion matrix** — understand which classes are being confused
- **ROC-AUC** — overall discriminative ability

Target for v1 prototype:
- Phishing recall ≥ 0.85 (don't miss real threats)
- Spam precision ≥ 0.90 (don't escalate spam to analysts)
- Overall false positive reduction vs. baseline: 40–50%

---

## 10. Key Challenges

- **Class imbalance:** Phishing samples are rare — requires careful sampling and loss weighting
- **Concept drift:** Phishing tactics evolve — model must be retrained periodically
- **Adversarial inputs:** Attackers will probe and adapt — model must not rely on easily-gamed features
- **Explainability:** Analysts need to understand why an email was flagged — feature attribution is required
- **Data quality:** Public datasets may contain outdated or mislabeled samples — validation is critical

---

## 11. Future Directions (Out of Scope for v1)

- Continual learning for real-time model adaptation
- Multilingual detection
- Integration with M365, SIEM, or SOAR platforms
- Cross-channel correlation (email + SMS + voice)
- Graph-based campaign detection (linking related phishing emails by infrastructure)
- LLM-based reasoning for ambiguous case explanation

---

## 12. Conclusion

The recommended approach is a staged, prototype-first architecture: start with an interpretable feature-based model, layer in transformer-based semantic understanding, and fuse outputs into a calibrated ensemble. The 3-bucket output with confidence scores and manual review flags directly addresses the SOC analyst workload problem. Accuracy improves iteratively through the analyst feedback loop.
