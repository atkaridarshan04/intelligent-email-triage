# Classification Logic: Binary Model with Confidence-Based Review Routing

## Overview

Every user-reported email is classified by a **binary model** (Spam / Phishing) and then routed to one of three operational outcomes: **Spam**, **Phishing**, or **Analyst Review**.

**Analyst Review is not a model class.** It is an operational routing state triggered when the model's confidence is insufficient to automate a decision.

```
Model learns:     Spam | Phishing
Runtime outputs:  Spam | Phishing | Analyst Review
```

---

## Signal Categories

The following signal categories are extracted from every email.

### 1. Sender Structure Signals

- **Display name / From mismatch:** The display name shows a trusted name but the actual From address is unrelated
- **Reply-to mismatch:** Reply-to domain differs from From domain — common in phishing to redirect replies to attacker-controlled inbox
- **Free-email sender:** Sender uses a free provider (Gmail, Yahoo, Outlook) to impersonate a corporate or brand identity

---

### 2. URL Signals

- **URL count and domain count:** High URL count is a spam signal; single high-risk URL is a phishing signal
- **Shortened URLs:** Presence of URL shorteners (bit.ly, tinyurl, etc.) — flagged as a signal
- **Suspicious TLDs:** `.xyz`, `.top`, `.tk`, `.ml`, `.ga`, `.click` — commonly used in phishing infrastructure
- **IP literal URL:** URL uses an IP address as host (e.g., `http://192.168.1.1/login`) — legitimate services don't do this
- **URL entropy:** High-entropy domain names indicate algorithmically generated phishing infrastructure
- **Typosquatting similarity:** Domain uses character substitution to mimic a trusted brand (e.g., `paypa1.com`, `micros0ft.com`) — detected via edit distance against a list of known brand domains with Unicode normalization

---

### 3. Attachment Signals

| Attachment Type | Risk Level |
|---|---|
| Executable (.exe, .bat, .cmd, .ps1) | Critical |
| Macro-enabled Office (.xlsm, .docm, .pptm) | High |
| Password-protected ZIP/RAR | High |
| Archive from unknown sender | Medium-High |
| Standard Office with embedded macros | Medium |

---

### 4. Content and Semantic Signals

**Urgency indicators:**
- Time pressure: "within 24 hours", "immediately", "urgent action required"
- Threat language: "your account will be suspended", "unauthorized access detected"

**Credential request signals:**
- Explicit: "enter your password", "verify your credentials"
- Implicit: "click here to secure your account", "update your payment information"

**Impersonation signals:**
- Known brand names in subject or body
- Executive name or title in From display field
- Internal team impersonation (IT Helpdesk, HR, Finance)

**Financial context signals:**
- Wire transfer requests, invoice or payment references with urgency
- Gift card requests, payroll redirect requests

---

### 5. Statistical Text Signals

- **Uppercase ratio:** Excessive capitalization is a spam/phishing signal
- **Punctuation density:** Unusual punctuation patterns
- **Link density:** Ratio of links to text content
- **Subject and body length:** Unusually short or long content patterns

---

### 6. Brand Impersonation Signals

- Known brand mention detected in subject or body
- Sender domain does not match the mentioned brand
- Impersonation consistency check: brand name present but sender infrastructure inconsistent

---

## Per-Class Signal Definitions

### Class 1: Spam

**Definition:** Unsolicited bulk email with no targeted malicious intent.

**Positive signals:**
- Promotional, sensational, or clickbait language
- High URL count pointing to commercial domains
- No credential requests, no financial fraud context, no impersonation
- Unsubscribe link present
- Image-heavy with minimal text (common in marketing spam)
- Generic greeting, no recipient personalization
- Bulk messaging structure

**Signals that rule out spam:**
- Any credential request → elevate to Phishing
- Lookalike or newly registered domain → elevate to Phishing
- Executive impersonation → elevate to Phishing
- Malicious attachment → elevate to Phishing

**SOC Action:** Auto-suppress.

---

### Class 2: Phishing

**Definition:** Email designed to steal credentials, deliver malware, initiate financial fraud, or compromise systems.

**Positive signals:**

*Sender:*
- Display name / From mismatch
- Reply-to mismatch
- Free-email sender impersonating a brand or executive

*URL:*
- Typosquatting domain (edit distance ≤ 2 from known brand domain)
- IP address as URL host
- Suspicious TLD (`.xyz`, `.top`, `.tk`, `.ml`, `.ga`, `.click`)
- URL shortener with unknown destination
- High URL entropy

*Content:*
- Explicit credential request
- Executive impersonation + financial request (BEC pattern)
- Brand impersonation with login link
- Urgency + threat + credential request combination
- Financial fraud context (wire transfer, invoice, gift card, payroll redirect)

*Attachment:*
- Executable attachment
- Macro-enabled Office file
- Password-protected archive from unknown sender

**SOC Action:** Immediate escalation and investigation.

---

### Operational Output: Analyst Review

**Definition:** Not a model class. An operational routing state assigned when the model cannot make a high-confidence determination.

**Why it is not trained as a class:**
- "Review" represents uncertainty, not a semantic email category
- There are no natural training labels for "review" — labels exist for spam and phishing
- Training a third class on artificially constructed "review" labels introduces noise and degrades calibration

**Routing conditions (applied post-inference):**
- No class probability exceeds its confidence threshold
- The two class probabilities are within 0.15 of each other (ambiguous prediction)
- BEC pattern detected — always routed regardless of confidence (no links/attachments + executive impersonation + financial context)
- Any high-weight signal present in an email otherwise classified as Spam

**SOC Action:** Full manual triage required.

---

## Confidence Scoring

The model outputs probabilities for two classes (Spam, Phishing). A composite **Trust Score** (0–100) is computed before any routing decision:

```
trust_score = w1 * max_prob + w2 * margin_score
```

- **max_prob** — highest calibrated class probability
- **margin_score** — gap between the two class probabilities

Raw probabilities are calibrated via temperature scaling before trust score computation.

**Routing thresholds:**

| Trust Score | Routing Decision |
|---|---|
| > 90 | Auto-classify |
| 75 – 90 | Auto-classify with monitoring flag |
| 55 – 75 | Analyst Review queue |
| < 55 | Priority Analyst Review |

**Security override:** If phishing probability > 0.70 and any high-weight malicious signal is present, escalate immediately regardless of trust score.

See `confidence-and-explainability.md` for the full specification.

---

## Signal Priority and Weighting

### High-weight signals (any one is sufficient to push toward Phishing + Analyst Review)
- Credential request in body
- Lookalike or typosquatting domain
- Executive impersonation + financial request (BEC pattern)
- Executable or macro-enabled attachment from unknown sender
- IP address as URL host

### Medium-weight signals (two or more in combination push toward Phishing)
- Reply-to mismatch
- Free-email sender impersonating a brand
- Urgency language without credential request
- Suspicious URL structure (not confirmed malicious)
- Suspicious TLD
- URL shortener presence

### Low-weight signals (context-dependent, contribute to scoring but not decisive alone)
- High uppercase ratio
- High punctuation density
- High link density
- Generic greeting
- Image-only email body

### Spam-positive signals (reduce phishing score)
- Unsubscribe link present
- No credential request, no financial context, no impersonation
- High URL count to commercial domains
- Promotional language without urgency

---

## Classification Flow

```
Email Input
    │
    ├─ Parse headers, body, URLs, attachments
    │
    ├─ Extract signal categories:
    │   ├─ Sender structure (display/From mismatch, reply-to, free-email)
    │   ├─ URL signals (count, TLD, entropy, typosquatting, IP literal, shortener)
    │   ├─ Attachment signals (type, name pattern)
    │   ├─ Content signals (urgency, credential request, impersonation, financial)
    │   ├─ Statistical text signals (uppercase ratio, link density, length)
    │   └─ Brand impersonation signals
    │
    ├─ Run model inference (binary: Spam / Phishing) → raw logits
    │
    ├─ Temperature scaling → calibrated probabilities
    │
    ├─ Confidence Layer:
    │   ├─ Compute max_prob, margin_score
    │   ├─ Compute trust_score = w1*max_prob + w2*margin
    │   └─ Apply security override (phishing_prob > 0.70 + high-weight signal → escalate)
    │
    ├─ Route by trust_score:
    │   ├─ > 90  → auto-classify
    │   ├─ 75–90 → auto-classify + monitoring flag
    │   ├─ 55–75 → Analyst Review queue
    │   └─ < 55  → Priority Analyst Review
    │
    ├─ Tier 1 Explainability (inline):
    │   ├─ Rule summarizer → fast reasons from signal extraction
    │   └─ SHAP on structured feature MLP → feature contributions
    │
    └─ Final output: label + trust_score + spam_probability + phishing_probability + reasons[]

    [Async — post-routing, delivered to analyst interface]
    └─ Integrated Gradients on transformer → token attribution → rule summarizer phrases
```
