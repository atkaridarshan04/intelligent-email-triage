# Problem Formulation & Modeling Approach

## Overview

This project builds an AI-assisted SOC (Security Operations Center) triage system for **user-reported suspicious emails**.

The objective is not to fully automate enterprise email security decisions, but to reduce analyst workload by safely filtering low-risk nuisance emails while rapidly escalating likely malicious threats.

The final operational behavior is:

- classify suspicious reported emails as:
  - **Spam**
  - **Phishing**
- route uncertain cases to:
  - **Analyst Review**

This formulation was intentionally chosen after evaluating multiple alternative problem definitions.

---

# Problem Context

A naïve framing of email security classification often assumes a full enterprise mail classification problem, where every incoming email must be categorized into a broad taxonomy.

However, this project operates in a very different environment.

The input is not:

> all incoming organizational email

The input is:

> emails already reported by users as suspicious.

This distinction fundamentally changes the problem.

The system is not answering:

> “Is this email legitimate?”

Instead, it answers:

> “Among emails users considered suspicious enough to report, which ones are likely nuisance spam and which ones are likely malicious phishing attempts?”

This narrower framing aligns much better with SOC operational workflows.

---

# Alternative Problem Formulations Considered

Several broader formulations were evaluated before arriving at the final design.

---

## Option 1: Multi-Class Classification (Spam / Junk / Phishing / Analyst Review)

An early formulation proposed:

- Spam
- Junk
- Phishing
- Analyst Review

The idea was to distinguish:

- obvious nuisance mail
- suspicious gray-area content
- clearly malicious attacks

At first glance, this appears operationally expressive.

However, several issues emerged.

---

### Ambiguous Label Boundaries

The distinction between **spam** and **junk** proved difficult to define consistently.

Example:

```text
Exclusive investment opportunity available for selected users
````

Possible interpretations:

* promotional spam
* scam-adjacent junk
* phishing precursor

This creates annotation inconsistency.

---

### Label Noise

If different reviewers disagree frequently on the same sample, the model receives contradictory supervision.

This leads to:

* unstable decision boundaries
* degraded learning
* unreliable evaluation metrics

A noisy class definition harms performance more than a simpler but cleaner formulation.

---

### Limited Operational Benefit

From an SOC perspective, the critical distinction is often:

* nuisance
  vs
* malicious threat

The spam/junk distinction introduces additional complexity without proportionate operational value.

---

## Decision

The junk class was rejected.

---

## Option 2: Multi-Class Classification with Legitimate Class

A second formulation considered:

* Legitimate
* Spam
* Junk
* Phishing
* Analyst Review

This resembles broader enterprise email classification.

However, this project does not classify the entire enterprise email stream.

The input consists only of suspicious user-reported emails.

---

### Operational Misalignment

A broad legitimate class assumes the model must recognize normal business email.

That is not the primary task here.

The operational question is not:

> “Is this safe enterprise communication?”

but rather:

> “What should the SOC do with this suspicious report?”

---

### Dataset Feasibility Problems

A legitimate class would require collecting realistic benign-but-suspicious emails such as:

* real Microsoft alerts
* password reset notifications
* genuine vendor invoices
* cloud service security alerts
* workflow approvals
* enterprise notification emails

Public datasets with sufficient quality and diversity for this specific use case are limited.

This would significantly increase data acquisition complexity.

---

### Conservative SOC Design

For a safety-oriented triage assistant, uncertain benign-looking emails can simply be routed to analyst review.

A dedicated automated legitimate class is not required.

---

## Decision

The legitimate class was rejected.

---

# Final Problem Reduction

After evaluating these alternatives, the task was reduced to:

## Binary Classification

* **Spam**
* **Phishing**

with:

## Confidence-Based Human Escalation

* **Analyst Review**

for uncertain predictions.

---

# Why Binary Classification Was Chosen

## Cleaner Label Semantics

The binary distinction is operationally clear.

### Spam

Characteristics:

* unsolicited
* promotional
* nuisance communication
* low security risk
* bulk messaging

Examples:

* marketing campaigns
* affiliate promotions
* newsletters
* discount offers

---

### Phishing

Characteristics:

* credential theft attempts
* impersonation
* invoice/payment fraud
* malicious attachments
* social engineering attacks

Examples:

* Microsoft credential phishing
* payroll impersonation
* invoice malware delivery
* fake security notifications

---

The decision boundary is much easier to define consistently.

---

## Reduced Label Noise

Cleaner class definitions improve:

* annotation consistency
* model learnability
* evaluation reliability

The classifier learns a more stable decision surface.

---

## Better Dataset Feasibility

High-quality public datasets exist for:

* spam
* phishing

Whereas realistic datasets for:

* suspicious benign reports
* gray-area junk

are significantly harder to assemble at scale.

Binary reduction makes the dataset problem substantially more tractable.

---

## Safer Operational Behavior

Binary classification does not force ambiguous samples into incorrect automated decisions.

Instead:

low-confidence cases are escalated.

This is safer than introducing weakly defined automation classes.

---

# Final Operational Workflow

The final system behaves as follows:

```text
User-reported suspicious email
            ↓
     AI classification
            ↓
  Spam probability / Phishing probability
            ↓
    Confidence assessment
            ↓
 ┌─────────────────────────────────────┐
 │ High-confidence spam      → suppress │
 │ High-confidence phishing  → escalate │
 │ Low confidence            → analyst  │
 └─────────────────────────────────────┘
```

This creates a conservative human-in-the-loop triage assistant.

---

# Modeling Approach

## Hybrid Multimodal Design

The final model combines:

### Semantic Understanding

Transformer-based language modeling over email text.

Inputs:

* subject
* body text

Purpose:

* understand phishing persuasion
* detect social engineering semantics
* distinguish spam language patterns

A RoBERTa-style encoder is appropriate here.

---

### Structured Feature Learning

Parallel structured feature modeling over deterministic extracted signals.

Examples:

* sender mismatch indicators
* reply-to inconsistencies
* URL structure
* shortened links
* suspicious TLDs
* typosquatting similarity
* attachment risk indicators
* text statistical features
* brand impersonation mismatch

Purpose:

capture structural phishing/spam signals not purely semantic in nature.

---

### Fusion Classification

Semantic and structured representations are fused into a joint classifier.

Output:

```text
spam probability
phishing probability
```

---

### Confidence Routing Layer

A confidence mechanism determines whether automation is safe.

Behavior:

* high confidence → automated action
* low confidence → analyst review

This ensures conservative deployment behavior.

---

# Why This Architecture

This design balances:

## Practical Dataset Reality

Public datasets are heterogeneous and often incomplete.

The architecture avoids dependence on unavailable enterprise telemetry.

---

## Strong Generalization

The transformer learns semantic attack patterns.

Structured features provide complementary infrastructure signals.

This reduces over-reliance on either modality alone.

---

## Operational Explainability

Structured features improve interpretability.

Analysts can understand signals such as:

* suspicious sender mismatch
* risky URL structure
* malicious attachment indicators

rather than relying solely on opaque text classification.

---

## Security Safety

No LLM-based reasoning is used in the classification pipeline.

This avoids:

* prompt injection risks
* non-deterministic inference behavior
* security policy ambiguity

---

# Design Philosophy

This project intentionally prioritizes:

* conservative automation
* human oversight
* realistic dataset feasibility
* clean problem formulation
* robust multimodal learning
* operational SOC relevance

rather than unnecessary taxonomy complexity or unsafe autonomous decision-making.