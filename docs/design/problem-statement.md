# Problem Statement: AI-Assisted SOC Triage for User-Reported Suspicious Emails

## Background

Security Operations Centers receive large volumes of user-reported suspicious emails. Users are not expected to distinguish spam from phishing — everything they consider suspicious lands in the analyst queue. This creates significant noise: a large portion of reported emails are unsolicited bulk mail or promotional content, not malicious attacks.

Existing tooling flags both spam and phishing with similar confidence levels, leaving analysts to manually triage everything. This:

- Slows detection and response to real phishing threats
- Increases analyst fatigue from low-value investigations
- Raises the risk of missing or late-detecting actual attacks

## The Core Problem

The system is not answering:

> "Is this email legitimate?"

It is answering:

> "Among emails users considered suspicious enough to report, which are likely nuisance spam and which are likely malicious phishing attempts?"

This narrower framing aligns directly with SOC operational workflows.

## Objective

Build an AI-assisted triage system that classifies user-reported suspicious emails as **Spam** or **Phishing**, and routes uncertain cases to **Analyst Review** via confidence-based escalation.

```
Model learns:     Spam | Phishing
Runtime outputs:  Spam | Phishing | Analyst Review
```

The system produces a calibrated confidence score and machine-readable reasoning for every decision.

## Classification Outcomes

| Outcome | Risk | SOC Action |
|---|---|---|
| Spam | Low | Auto-suppress |
| Phishing | High | Immediate escalation + investigation |
| Analyst Review | Uncertain | Manual triage |

**Analyst Review is not a training label.** It is triggered dynamically through confidence calibration when the model cannot make a high-confidence determination. This preserves model purity and makes confidence calibration reliable.

## Signals the System Uses

Classification combines:

- **Email content and semantic intent** — urgency, impersonation, credential requests, social engineering tone
- **Sender structure** — display name / From mismatch, reply-to inconsistency, free-email sender usage
- **URL structure** — shortened links, suspicious TLDs, IP literal URLs, typosquatting indicators, domain entropy
- **Attachment indicators** — executables, macro-enabled documents, archives
- **Statistical text features** — uppercase ratio, punctuation density, link density, length patterns
- **Brand impersonation signals** — known brand mentions with sender-brand mismatch

## Constraints and Scope

- Training and validation use **publicly available datasets** only
- The system is a **standalone prototype** — no SOC platform integration required initially
- No LLM-based reasoning in the classification pipeline (prompt injection risk, non-deterministic behavior)
- No reliance on enterprise-only telemetry (SPF/DKIM/DMARC, IP reputation feeds, sender history) that is unavailable in public datasets

## Success Criteria

- Binary classifier (Spam / Phishing) with confidence-based Analyst Review routing
- Phishing recall > 98%
- Analyst queue reduction > 50%
- Calibrated confidence scores and machine-readable reasoning for every decision
- Conservative routing: uncertain cases escalate to analysts rather than being forced into incorrect automated decisions
