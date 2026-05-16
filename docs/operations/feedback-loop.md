# Analyst Feedback Loop Design

## Overview

The feedback loop is the mechanism by which SOC analyst verdicts are fed back into the model to improve classification accuracy over time. This is critical because:

1. The model will not be highly accurate at launch — analyst corrections are the primary improvement signal
2. Phishing tactics evolve — the model must adapt to new patterns
3. Edge cases (BEC, AI-generated phishing) can only be learned reliably from real analyst decisions

---

## How It Works

### Step 1: Model Classifies Email

The system processes a reported email and produces:
- Classification: Spam / Phishing / Analyst Review
- Trust score and confidence
- Supporting reasons

### Step 2: Analyst Reviews

For emails routed to Analyst Review (or any email the analyst chooses to review):
- Analyst sees the model's classification and confidence
- Analyst sees the top signals that drove the classification
- Analyst can:
  - **Confirm** the model's classification (agree)
  - **Override** with a different classification (disagree)
  - **Escalate** (mark as requiring further investigation)
  - **Defer** (not enough information to decide)

### Step 3: Verdict Stored

The analyst's verdict is stored alongside:
- Original email features (not the raw email — features only, for privacy)
- Model's original prediction and confidence
- Analyst ID and timestamp
- Any notes the analyst adds

### Step 4: Feedback Processed

Stored verdicts are used in two ways:

**Threshold adjustment (immediate):**
If a specific signal combination is consistently being overridden, the confidence threshold for that pattern is adjusted.

**Scheduled model updates:**
- **Weekly:** Fine-tune classification head using new analyst-labeled data
- **Monthly:** Full retraining with all accumulated feedback
- New model is validated against held-out test set before deployment
- Performance comparison between old and new model is logged

---

## Feedback Data Schema

```json
{
  "email_id": "unique identifier",
  "timestamp_reported": "ISO 8601",
  "model_prediction": {
    "classification": "Spam" | "Phishing" | "Analyst Review",
    "spam_probability": 0.0,
    "phishing_probability": 0.0,
    "trust_score": 0
  },
  "analyst_verdict": {
    "classification": "Spam" | "Phishing" | "escalate" | "defer",
    "analyst_id": "anonymized",
    "timestamp": "ISO 8601",
    "notes": "optional free text"
  },
  "agreement": true | false,
  "features_snapshot": {
    "display_from_mismatch": true | false,
    "reply_to_mismatch": true | false,
    "suspicious_url_present": true | false,
    "has_attachment": true | false,
    "brand_impersonation": true | false
  }
}
```

---

## Retraining Trigger Conditions

| Condition | Threshold |
|---|---|
| New analyst-labeled samples accumulated | ≥ 200 new samples |
| Model override rate exceeds baseline | > 20% of reviewed emails overridden |
| New phishing campaign pattern detected | Manual trigger |
| Scheduled head fine-tune | Weekly |
| Scheduled full retraining | Monthly |

---

## Preventing Feedback Poisoning

Analyst feedback is trusted but not blindly applied:

- **Minimum analyst agreement:** If multiple analysts review the same email and disagree, the verdict is flagged for team discussion before being added to training data
- **Outlier detection:** Verdicts statistically inconsistent with the analyst's historical pattern are flagged for review
- **Holdout validation:** After retraining, the new model must match or exceed the previous model's performance on the held-out test set before deployment
- **Audit log:** All feedback and retraining events are logged for traceability

---

## Analyst Interface Requirements (v1)

Minimum requirements:

- Display model classification + confidence for each reviewed email
- Show top 3–5 signals that drove the classification
- One-click confirm / override buttons
- Override requires selecting the correct classification (Spam / Phishing)
- Optional notes field
- Verdict submission stores to feedback database

---

## Metrics to Track

| Metric | Purpose |
|---|---|
| Override rate (overall) | How often analysts disagree with the model |
| Override rate by class | Which class has the most errors |
| Override rate over time | Is the model improving? |
| Confidence calibration error | Are high-confidence predictions actually correct? |
| Analyst Review routing rate | % of emails routed to review (should decrease over time) |

These metrics are reviewed at each retraining cycle to guide model improvement priorities.

---

## Long-Term Vision (Post-v1)

- Active learning: model proactively requests analyst labels for the most uncertain emails
- Automated retraining pipeline triggered by drift detection
- Analyst agreement scoring to weight high-accuracy analysts more heavily
- Integration with SOC ticketing system for seamless verdict capture
