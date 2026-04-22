# Classification Logic: 3-Bucket Email Categorization

## Overview

Every user-reported email is classified into one of three buckets. This document defines the complete classification logic — the full set of detection signals per bucket, authentication analysis, domain spoofing detection, confidence scoring, and manual review rules.

---

## Signal Categories

Before defining per-bucket logic, these are the signal categories extracted from every email:

### 1. Authentication Signals
Email authentication protocols tell us whether the sender is who they claim to be.

| Signal | What It Checks | Failure Meaning |
|---|---|---|
| SPF | Sender's IP is authorized to send for the From domain | Domain is spoofed or misconfigured |
| DKIM | Email content hasn't been tampered with; signed by sending domain | Message integrity compromised or forged |
| DMARC | Enforces SPF/DKIM alignment; defines policy (none/quarantine/reject) | Domain owner has no control over who sends in their name |

**Authentication result combinations and their weight:**

| SPF | DKIM | DMARC | Interpretation | Weight |
|---|---|---|---|---|
| Pass | Pass | Pass | Fully authenticated | Low phishing signal |
| Pass | Pass | Fail | Alignment issue — domain mismatch | Medium |
| Pass | Fail | Fail | Partial auth — suspicious | Medium-High |
| Fail | Pass | Fail | IP not authorized — suspicious | Medium-High |
| Fail | Fail | Fail | No authentication at all | High phishing signal |
| Pass | None | None | Bulk mail pattern (no DKIM/DMARC configured) | Spam/Gray signal |
| None | None | None | No auth records — unverifiable sender | High phishing signal |

**Important:** Authentication failure alone does not confirm phishing — many legitimate small businesses have misconfigured email. It is a signal, not a verdict. It must be combined with other signals.

---

### 2. Domain and Sender Signals

**Domain spoofing detection:**
- **Lookalike domain:** Domain uses character substitution to mimic a trusted brand (e.g., `paypa1.com`, `rn` instead of `m`, `micros0ft.com`). Detected via edit distance comparison against a list of known brand domains and homograph character mapping.
- **Subdomain abuse:** Legitimate domain used as subdomain of attacker domain (e.g., `paypal.com.attacker.net` — the actual domain is `attacker.net`)
- **Newly registered domain:** Domain registered < 30 days ago. Phishing infrastructure is typically short-lived.
- **Domain age vs. email volume mismatch:** New domain sending high email volume is a strong phishing signal.
- **Display name spoofing:** The display name shows a trusted name (e.g., "Microsoft Security") but the actual From address is unrelated. Detected by comparing display name against known brand/executive names while checking the actual domain.
- **Reply-to mismatch:** Reply-to address domain differs from From address domain. Common in phishing to redirect replies to attacker-controlled inbox.
- **Cousin domain:** Domain is registered to look like an internal or partner domain (e.g., `company-support.com` vs. `company.com`).

**Sender reputation signals:**
- IP address listed in public threat intelligence feeds (Spamhaus, SURBL, etc.)
- Sending IP belongs to known bulk mail provider vs. corporate mail server
- Sender domain has no MX record (cannot receive replies — common in throwaway phishing domains)
- Sender domain has no website or a newly created placeholder site

---

### 3. Content and Semantic Signals

**Urgency indicators:**
- Time pressure language: "within 24 hours", "immediately", "urgent action required"
- Threat language: "your account will be suspended", "unauthorized access detected", "legal action"
- Scarcity language: "limited time", "last chance", "final notice"

**Credential request signals:**
- Explicit requests: "enter your password", "verify your credentials", "confirm your login"
- Implicit requests: "click here to secure your account", "update your payment information"
- Login link with urgency context

**Impersonation signals:**
- Known brand names in subject or body (Microsoft, PayPal, Amazon, Google, internal IT team names)
- Executive name or title in From display field (CEO, CFO, Director)
- Internal team impersonation (IT Helpdesk, HR, Finance, Security Team)
- Official-looking formatting mimicking known brand templates

**Financial context signals:**
- Wire transfer requests
- Invoice or payment references with urgency
- Gift card requests
- Bank account change requests
- Payroll redirect requests

**BEC-specific signals (no links, no attachments):**
- Executive impersonation + financial request + urgency = BEC pattern
- Conversational tone with unusual request
- "Can you handle this discreetly?" type language

---

### 4. URL and Link Signals

**Static URL analysis:**
- Homograph characters in domain (Unicode lookalikes: `аpple.com` using Cyrillic `а`)
- Suspicious TLDs: `.xyz`, `.top`, `.click`, `.tk`, `.ml`, `.ga` — commonly used in phishing infrastructure
- Excessive subdomains: `login.secure.verify.paypal.attacker.com`
- URL length anomaly: extremely long URLs used to obscure destination
- IP address as URL host (e.g., `http://192.168.1.1/login`) — legitimate services don't do this
- Port number in URL (e.g., `http://domain.com:8080/login`)
- Mismatch between anchor text and actual URL destination

**Redirect chain analysis:**
- URL shortener usage (bit.ly, tinyurl, etc.) — requires expansion to inspect final destination
- Open redirect abuse on legitimate domains (e.g., `google.com/url?q=malicious.com`)
- Multi-hop redirect chains (URL → URL → URL → phishing page)
- JavaScript-based redirects in HTML content

**URL count and distribution:**
- High number of URLs in a single email (spam signal)
- Single URL with high-risk characteristics (phishing signal)
- All URLs pointing to same domain (bulk mail signal)

---

### 5. Attachment Signals

| Attachment Type | Risk Level | Notes |
|---|---|---|
| Executable (.exe, .bat, .cmd, .ps1) | Critical | Never legitimate in email |
| Macro-enabled Office (.xlsm, .docm, .pptm) | High | Common malware delivery vector |
| Password-protected ZIP/RAR | High | Used to bypass attachment scanners |
| PDF with embedded links | Medium | Inspect links inside PDF |
| Standard Office (.xlsx, .docx, .pptx) | Low-Medium | Check for embedded macros |
| PDF without links | Low | Generally safe |
| Image only (.jpg, .png) | Low | Check for embedded URLs in HTML |

**Attachment name signals:**
- Invoice, payment, receipt, statement naming patterns combined with urgency
- Double extension abuse (e.g., `document.pdf.exe`)
- Generic names (`scan001.pdf`, `document.doc`) from unknown senders

---

### 6. Sender–Recipient Relationship Signals

- **First contact:** Has this sender (or sender domain) ever emailed this recipient before? First contact from an unknown domain with any phishing signal is elevated risk.
- **Communication frequency:** Sudden email from a domain that has never appeared in the recipient's history
- **Domain familiarity:** Is the sender domain known within the organization (partner, vendor, customer)?
- **Internal impersonation:** Email claims to be from an internal address but originates from an external domain

---

### 7. Behavioral and Metadata Signals

- **Off-hours sending:** Email sent at unusual times (2–5 AM local time) — common in automated phishing campaigns
- **Header routing anomalies:** Received headers show unexpected relay hops or geographic inconsistencies
- **HTML obfuscation:** Invisible text, zero-font-size text, or CSS-hidden content used to confuse content filters
- **Image-only email:** No text content — entire email is an image (used to bypass text-based filters)
- **HTML-to-text ratio:** Heavily HTML-formatted email with minimal readable text
- **Sending volume spike:** Sudden high-volume sending from a domain not previously seen at that volume

---

## Per-Bucket Signal Definitions

### Bucket 1: Spam / Junk

**Definition:** Unsolicited bulk email with no targeted malicious intent.

**Positive signals (spam indicators):**
- Sending IP belongs to known bulk mail infrastructure (Mailchimp, Constant Contact, SendGrid used without proper configuration)
- High sending volume from domain
- No personalization — generic greeting, no recipient name
- Promotional, sensational, or clickbait language
- SPF passes, DKIM/DMARC absent (typical of poorly configured bulk senders)
- Multiple URLs all pointing to commercial domains
- Unsubscribe link present
- No credential requests, no financial context, no impersonation
- Known spam campaign fingerprint (content matches known spam patterns)
- Image-heavy with minimal text (common in marketing spam)

**Negative signals (things that rule out spam):**
- Any authentication failure (SPF fail, DKIM fail) → elevate to gray or phishing
- Any credential request → elevate to phishing
- Lookalike or newly registered domain → elevate to phishing
- Executive impersonation → elevate to phishing

**SOC Action:** None. Auto-dismiss.

---

### Bucket 2: Gray / Bulk Email

**Definition:** Email from a legitimate or semi-legitimate sender that is unsolicited or ambiguous. Not clearly malicious, not clearly safe.

**Positive signals (gray indicators):**
- Sender domain is reputable and established (> 1 year old, has legitimate web presence)
- Authentication partially passes (SPF pass, DKIM fail — misconfiguration, not spoofing)
- Newsletter or mailing list structure (List-Unsubscribe header present)
- Automated notification pattern (password reset, account activity) from a domain the recipient has no history with
- Promotional content with account-related language but no explicit credential request
- Links go to known or semi-known domains (not newly registered, not flagged in threat intel)
- No executive impersonation, no financial fraud context
- First-contact sender but domain is established and reputable

**Signals that push gray toward phishing (trigger manual_review):**
- Any urgency language combined with account-related content
- Authentication failure (SPF fail) even from a reputable domain
- Any URL with redirect chain or suspicious structure
- Credential-adjacent language ("confirm your details", "update your information")
- Reply-to mismatch even from a legitimate domain

**SOC Action:** Minimal. Quick review or auto-dismiss with low-confidence flag.

---

### Bucket 3: Phishing

**Definition:** Email designed to steal credentials, deliver malware, initiate financial fraud, or compromise systems.

**Positive signals (phishing indicators):**

*Authentication:*
- SPF fail + DKIM fail (no authentication)
- DMARC reject or quarantine policy triggered
- None/None/None (no auth records at all)

*Domain:*
- Lookalike domain (edit distance ≤ 2 from known brand domain)
- Homograph domain (Unicode character substitution)
- Subdomain abuse (trusted brand as subdomain of attacker domain)
- Newly registered domain (< 30 days)
- Display name spoofing (trusted name, unrelated actual domain)
- Reply-to mismatch
- No MX record on sender domain

*Content:*
- Explicit credential request
- Executive impersonation + financial request (BEC)
- Brand impersonation with login link
- Urgency + threat + credential request combination
- Financial fraud context (wire transfer, invoice, gift card, payroll redirect)
- HTML obfuscation (invisible text, CSS hiding)

*URL:*
- Homograph characters in URL domain
- Redirect chain with suspicious final destination
- Open redirect abuse on legitimate domain
- IP address as URL host
- Suspicious TLD (.xyz, .top, .tk, .ml, .ga, .click)
- URL shortener with unknown destination

*Attachment:*
- Executable attachment
- Macro-enabled Office file
- Password-protected archive from unknown sender
- Double extension file

*Behavioral:*
- First-contact sender + authentication failure + urgency
- Off-hours sending + no prior relationship + suspicious content
- Header routing anomalies

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

## Signal Priority and Weighting

### High-weight signals (any one is sufficient to push toward phishing + manual review)
- Credential request in body
- SPF fail + DKIM fail (both failing together)
- Lookalike or homograph domain
- Known malicious URL or IP (confirmed threat intel hit)
- Executive impersonation + financial request (BEC pattern)
- Executable or macro-enabled attachment from unknown sender
- Subdomain abuse of trusted brand

### Medium-weight signals (two or more in combination push toward phishing)
- Single auth failure (SPF fail only or DKIM fail only)
- Urgency language without credential request
- First-contact sender from unknown domain
- Suspicious URL structure (not confirmed malicious)
- Reply-to mismatch
- Newly registered domain (< 30 days)
- Display name spoofing without domain confirmation
- Suspicious TLD

### Low-weight signals (context-dependent, contribute to scoring but not decisive alone)
- Generic greeting
- HTML-heavy formatting
- Unsubscribe link absent
- Off-hours sending time
- High URL count
- Image-only email body

### Spam/Gray-positive signals (reduce phishing score)
- Unsubscribe link present
- Known bulk mail infrastructure IP
- Established reputable sender domain (> 2 years, known web presence)
- SPF pass + DKIM pass + DMARC pass from reputable domain
- No credential request, no financial context, no impersonation

---

## Manual Review Flag

The `manual_review` flag is set to `true` when any of the following conditions are met:

1. Confidence score < 0.70 (configurable threshold)
2. Top two class probabilities are within 0.15 of each other
3. Email classified as gray but contains any phishing-adjacent signal (urgency + account language, auth failure, suspicious URL, credential-adjacent phrasing)
4. BEC pattern detected — always flagged regardless of confidence (no links/attachments + executive impersonation + financial context)
5. AI-generated content indicators present combined with any phishing signal
6. Any high-weight signal present in an email otherwise classified as gray
7. Attachment present from first-contact sender regardless of attachment type

---

## Edge Cases and Decision Rules

| Scenario | Classification | manual_review |
|---|---|---|
| Spam content + suspicious URL | Gray | true |
| Legitimate domain + credential request in body | Phishing | true |
| No links, no attachments, urgency + financial request | Phishing (BEC) | true (always) |
| Newsletter + SPF fail | Gray | true |
| First contact + perfect grammar + no signals | Gray | true if any secondary signal present |
| SPF fail + DKIM fail + no other signals | Gray | true |
| Known bulk sender + urgency language | Gray | true |
| Lookalike domain + no other signals | Phishing | true |
| Reputable domain + DKIM fail only | Gray | false (unless other signals present) |
| Executable attachment from unknown sender | Phishing | true (always) |
| Open redirect on legitimate domain | Gray/Phishing | true |

---

## Classification Flow

```
Email Input
    │
    ├─ Parse headers, body, URLs, attachments
    │
    ├─ Extract all signal categories:
    │   ├─ Authentication (SPF/DKIM/DMARC results + alignment)
    │   ├─ Domain signals (lookalike, age, spoofing, reply-to mismatch)
    │   ├─ Content signals (urgency, credential request, impersonation, financial)
    │   ├─ URL signals (homograph, redirect chain, TLD, shortener)
    │   ├─ Attachment signals (type, name pattern)
    │   ├─ Sender–recipient relationship (first contact, domain familiarity)
    │   └─ Behavioral signals (off-hours, header anomalies, HTML obfuscation)
    │
    ├─ Apply signal weighting → compute per-class scores
    │
    ├─ Run model inference (Stage 1 + Stage 2 ensemble) → class probabilities
    │
    ├─ Apply confidence calibration (Platt scaling)
    │
    ├─ Apply override rules:
    │   ├─ Any high-weight signal → floor phishing probability at 0.60
    │   ├─ BEC pattern → classify phishing, force manual_review
    │   └─ Spam-positive signals present → reduce phishing probability
    │
    ├─ Determine final classification + confidence score
    │
    └─ Set manual_review flag per rules above
```
