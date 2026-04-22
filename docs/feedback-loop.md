# Analyst Feedback Loop Design

## Overview

The feedback loop is the mechanism by which SOC analyst verdicts are fed back into the model to improve classification accuracy over time. This is critical because:

1. The model will not be highly accurate at launch — analyst corrections are the primary improvement signal
2. Phishing tactics evolve — the model must adapt to new patterns
3. Organization-specific patterns (known senders, internal communication norms) can only be learned from real analyst decisions

---

## How It Works

### Step 1: Model Classifies Email

The system processes a reported email and produces:
- Classification: spam / gray / phishing
- Confidence score
- Manual review flag (if applicable)
- Supporting signals

### Step 2: Analyst Reviews

For emails flagged for manual review (or any email the analyst chooses to review):
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

**Immediate (threshold adjustment):**
- If a specific signal combination is consistently being overridden, the confidence threshold for that pattern is adjusted
- Example: If "SPF fail + newsletter content" is consistently being reclassified from phishing to gray, the model's weighting for that combination is updated

**Periodic retraining:**
- Accumulated analyst-labeled data is added to the training set
- Model is retrained on a schedule (e.g., monthly or when N new labeled samples are available)
- New model is validated against held-out test set before deployment
- Performance comparison between old and new model is logged

---

## Feedback Data Schema

```
{
  "email_id": "unique identifier",
  "timestamp_reported": "ISO 8601",
  "model_prediction": {
    "classification": "spam" | "gray" | "phishing",
    "confidence": 0.0 – 1.0,
    "manual_review": true | false
  },
  "analyst_verdict": {
    "classification": "spam" | "gray" | "phishing" | "escalate" | "defer",
    "analyst_id": "anonymized",
    "timestamp": "ISO 8601",
    "notes": "optional free text"
  },
  "agreement": true | false,
  "features_snapshot": {
    "url_risk": "low" | "medium" | "high",
    "auth_failures": [...],
    "intent_signals": [...],
    "sender_first_contact": true | false
  }
}
```

---

## Retraining Trigger Conditions

Retraining is triggered when any of the following conditions are met:

| Condition | Threshold |
|---|---|
| New analyst-labeled samples accumulated | ≥ 200 new samples |
| Model override rate exceeds baseline | > 20% of reviewed emails overridden |
| New phishing campaign pattern detected | Manual trigger by team |
| Scheduled retraining | Monthly |

---

## Preventing Feedback Poisoning

Analyst feedback is trusted but not blindly applied:

- **Minimum analyst agreement:** If multiple analysts review the same email and disagree, the verdict is flagged for team discussion before being added to training data
- **Outlier detection:** Verdicts that are statistically inconsistent with the analyst's historical pattern are flagged for review
- **Holdout validation:** After retraining, the new model must match or exceed the previous model's performance on the held-out test set before deployment
- **Audit log:** All feedback and retraining events are logged for traceability

---

## Analyst Interface Requirements (v1)

The feedback interface does not need to be complex in v1. Minimum requirements:

- Display model classification + confidence for each reviewed email
- Show top 3–5 signals that drove the classification (explainability)
- One-click confirm / override buttons
- Override requires selecting the correct classification from a dropdown
- Optional notes field
- Verdict submission stores to feedback database

This can be a simple web form or CLI tool in the prototype phase.

---

## Metrics to Track

| Metric | Purpose |
|---|---|
| Override rate (overall) | How often analysts disagree with the model |
| Override rate by class | Which bucket has the most errors |
| Override rate over time | Is the model improving? |
| Confidence calibration error | Are high-confidence predictions actually correct? |
| Time-to-verdict | How long analysts spend on manual review emails |

These metrics are reviewed at each retraining cycle to guide model improvement priorities.

---

## Long-Term Vision (Post-v1)

- Active learning: model proactively requests analyst labels for the most uncertain emails
- Automated retraining pipeline triggered by drift detection
- Analyst agreement scoring to weight high-accuracy analysts more heavily
- Integration with SOC ticketing system for seamless verdict capture
