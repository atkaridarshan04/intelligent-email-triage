# Classification Logic: 3-Bucket Email Categorization

## Overview

Every user-reported email is classified into one of three buckets. This document defines the classification logic — what signals map to which bucket, how confidence is determined, and when the manual review flag is triggered.

---

## The Three Buckets

### Bucket 1: Spam / Junk

**Definition:** Unsolicited email with no targeted malicious intent. Sent in bulk, typically for commercial or nuisance purposes.

**Signals that indicate Spam:**
- High-volume sending pattern from sender domain
- No personalization (generic greeting, no recipient name)
- Promotional language without credential requests
- Sender domain is a known bulk mail provider
- SPF passes but DKIM/DMARC are absent (common in bulk mail)
- No suspicious URLs (links go to known commercial domains)
- Unsubscribe link present
- No attachment or only marketing-type attachments (PDF brochures)
- Email matches known spam campaign patterns

**SOC Action:** None. Auto-dismiss.

---

### Bucket 2: Gray / Bulk Email

**Definition:** Email from a legitimate or semi-legitimate sender that the recipient didn't explicitly request, or bulk mail with ambiguous characteristics. Not clearly malicious, but not clearly safe either.

**Signals that indicate Gray:**
- Sender is a known legitimate domain but email was unsolicited
- Newsletter or mailing list characteristics without explicit opt-in evidence
- Automated notification from a service (password reset, account alert) where sender legitimacy is uncertain
- Moderate urgency language without explicit credential requests
- Links present but going to known or semi-known domains
- Authentication partially passes (e.g., SPF pass, DKIM fail)
- No prior communication history with sender but domain is reputable
- Content is promotional but includes account-related language

**SOC Action:** Minimal. Quick review or auto-dismiss with low-confidence flag.

---

### Bucket 3: Phishing

**Definition:** Email designed to steal credentials, deliver malware, initiate financial fraud, or compromise systems. Includes spear phishing, BEC, and AI-generated phishing.

**Signals that indicate Phishing:**
- Explicit credential request ("enter your password", "verify your account")
- Impersonation of known brand, executive, or internal team
- Authentication failures: SPF fail, DKIM fail, DMARC reject/quarantine
- Sender domain is newly registered (< 30 days) or lookalike domain
- Reply-to address differs from From address
- URLs with redirect chains, homograph characters, or suspicious TLDs
- Urgency + threat combination ("your account will be suspended in 24 hours")
- Financial context with urgency (wire transfer, invoice, gift card requests)
- No prior sender–recipient communication history
- IP reputation flagged in threat intelligence feeds
- Attachment with executable, macro-enabled, or password-protected content
- HTML content heavily obfuscated or using invisible text

**SOC Action:** Full triage and response required.

---

## Confidence Scoring

Each classification comes with a confidence score (0.0 – 1.0).

| Confidence Range | Interpretation |
|---|---|
| 0.85 – 1.00 | High confidence — auto-classify |
| 0.70 – 0.84 | Moderate confidence — classify with note |
| 0.50 – 0.69 | Low confidence — flag for manual review |
| < 0.50 | Very low confidence — always manual review |

---

## Manual Review Flag

The `manual_review` flag is set to `true` when any of the following conditions are met:

1. Confidence score is below the configured threshold (default: 0.70)
2. Email is classified as "gray" but contains one or more phishing-adjacent signals (urgency, credential request, auth failure, suspicious URL)
3. The model's top two predicted classes are within 0.15 of each other (ambiguous boundary)
4. Email contains BEC-pattern signals (no links/attachments, executive impersonation, financial context) — these are always flagged regardless of confidence
5. Email contains AI-generated content indicators combined with any phishing signal

---

## Signal Priority and Weighting

Not all signals are equal. The following hierarchy applies when signals conflict:

**High-weight signals (strong phishing indicators):**
- Credential request in body
- Authentication failure (SPF fail + DKIM fail together)
- Lookalike or newly registered domain
- Known malicious URL or IP
- Executive impersonation with financial request

**Medium-weight signals:**
- Single auth failure (SPF fail only or DKIM fail only)
- Urgency language without credential request
- First-contact sender
- Suspicious URL structure (not confirmed malicious)
- Reply-to mismatch

**Low-weight signals (context-dependent):**
- Generic greeting
- HTML-heavy formatting
- Unsubscribe link absent
- Off-hours sending time

A single high-weight signal is sufficient to push classification toward phishing with a manual review flag. Multiple medium-weight signals in combination can also trigger phishing classification.

---

## Edge Cases and Decision Rules

### "Looks like spam but has a suspicious URL"
→ Classify as **gray**, set `manual_review: true`, flag URL risk as high

### "Legitimate sender domain but credential request in body"
→ Classify as **phishing** — legitimate senders don't ask for credentials via email

### "No links, no attachments, urgency + financial request"
→ Classify as **phishing (BEC pattern)**, always set `manual_review: true`

### "Newsletter with SPF fail"
→ Classify as **gray**, note authentication anomaly, low confidence

### "First-contact email with perfect grammar, no obvious signals"
→ Classify as **gray** with moderate confidence, flag for review if any secondary signal present

---

## Classification Flow Summary

```
Email Input
    │
    ├─ Extract signals (content, URL, metadata, sender-recipient, behavioral)
    │
    ├─ Score each signal category
    │
    ├─ Run model inference → raw class probabilities
    │
    ├─ Apply confidence calibration
    │
    ├─ Apply edge case rules (BEC pattern, high-weight signal override)
    │
    ├─ Determine final classification + confidence score
    │
    └─ Set manual_review flag if confidence < threshold or edge case triggered
```
