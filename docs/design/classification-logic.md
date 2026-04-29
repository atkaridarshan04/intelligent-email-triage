# Classification Logic: 3-Class Model with Uncertainty-Driven Review Routing

## Overview

Every user-reported email is classified by a **3-class model** (Spam, Junk, Phishing) and then routed to one of four operational outcomes: **Spam**, **Junk**, **Phishing**, or **Analyst Review**.

**Analyst Review is not a model class.** It is an operational routing state triggered when the model's confidence is insufficient to automate a decision. This separation keeps training data clean and makes confidence calibration reliable.

```
Model learns:     Spam | Junk | Phishing
Runtime outputs:  Spam | Junk | Phishing | Analyst Review
```

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
| Pass | None | None | Bulk mail pattern (no DKIM/DMARC configured) | Spam/Junk signal |
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
- URL shortener usage (bit.ly, tinyurl, etc.) — flagged as a signal; not expanded inline
- Open redirect abuse on legitimate domains (e.g., `google.com/url?q=malicious.com`) — detected via static pattern matching
- Multi-hop redirect chain indicators in URL structure
- JavaScript-based redirects in HTML content

**Live URL following is not performed in the inline inference path.** Outbound HTTP requests to attacker-controlled URLs introduce SSRF risk and violate the <300ms latency budget. Redirect expansion runs in an isolated async enrichment sandbox post-routing if required.

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

## Per-Class Signal Definitions

The model is trained on three classes. Signal definitions below drive the model's learned representations and the post-inference routing logic.

### Class 1: Spam

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
- Any authentication failure (SPF fail, DKIM fail) → elevate to Junk or Phishing
- Any credential request → elevate to phishing
- Lookalike or newly registered domain → elevate to phishing
- Executive impersonation → elevate to phishing

**SOC Action:** Auto-folder.

---

### Class 2: Junk

**Definition:** Low-quality or suspicious nuisance traffic from a legitimate or semi-legitimate sender. Not clearly malicious, not clearly safe.

**Positive signals (Junk indicators):**
- Sender domain is reputable and established (> 1 year old, has legitimate web presence)
- Authentication partially passes (SPF pass, DKIM fail — misconfiguration, not spoofing)
- Newsletter or mailing list structure (List-Unsubscribe header present)
- Automated notification pattern (password reset, account activity) from a domain the recipient has no history with
- Promotional content with account-related language but no explicit credential request
- Links go to known or semi-known domains (not newly registered, not flagged in threat intel)
- No executive impersonation, no financial fraud context
- First-contact sender but domain is established and reputable

**Signals that push Junk toward Phishing or Analyst Review:**
- Any urgency language combined with account-related content
- Authentication failure (SPF fail) even from a reputable domain
- Any URL with redirect chain or suspicious structure
- Credential-adjacent language ("confirm your details", "update your information")
- Reply-to mismatch even from a legitimate domain

**SOC Action:** Junk route.

---

### Class 3: Phishing

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

### Operational Output: Analyst Review

**Definition:** Not a model class. An operational routing state assigned when the model cannot make a high-confidence determination.

**Why it is not trained as a class:**
- "Review" represents uncertainty, not a semantic email category
- There are no natural training labels for "review" — labels exist for spam, junk, and phishing
- Training a 4th class on artificially constructed "review" labels introduces noise and degrades calibration

**Routing conditions (applied post-inference):**
- No class probability exceeds its confidence threshold (see Confidence Scoring below)
- Top two class probabilities are within 0.15 of each other (ambiguous prediction)
- Junk classification with any phishing-adjacent signal (urgency + account language, auth failure, suspicious URL, credential-adjacent phrasing)
- BEC pattern detected — always routed regardless of confidence (no links/attachments + executive impersonation + financial context)
- AI-generated content indicators present combined with any phishing signal
- Any high-weight signal present in an email otherwise classified as Junk
- Attachment present from first-contact sender regardless of attachment type

**SOC Action:** Full manual triage required.


---

## Confidence Scoring

The model outputs probabilities for three classes (Spam, Junk, Phishing). A composite **Trust Score** (0–100) is computed from two signals before any routing decision is made:

- **Max probability** — highest calibrated class probability
- **Margin score** — gap between top two class probabilities (low margin = ambiguous prediction)

```
trust_score = w1 * max_prob + w2 * margin_score
```

Raw probabilities are calibrated via temperature scaling before trust score computation.

OOD novelty scoring is deferred to v2. See `confidence-and-explainability.md` for rationale.

**Routing thresholds:**

| Trust Score | Routing Decision |
|---|---|
| > 90 | Auto-classify |
| 75 – 90 | Auto-classify with low-priority monitoring flag |
| 55 – 75 | Analyst Review queue |
| < 55 | Priority Analyst Review |

**Security override:** If phishing probability > 0.70 and any high-weight malicious signal is present, escalate immediately regardless of trust score.

See `confidence-and-explainability.md` for the full specification.

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

### Spam/Junk-positive signals (reduce phishing score)
- Unsubscribe link present
- Known bulk mail infrastructure IP
- Established reputable sender domain (> 2 years, known web presence)
- SPF pass + DKIM pass + DMARC pass from reputable domain
- No credential request, no financial context, no impersonation

---

## Analyst Review Routing

The `analyst_review` flag is set to `true` (and the output label becomes "Analyst Review") when any of the following conditions are met:

1. No class probability exceeds its routing threshold (see Confidence Scoring above)
2. Top two class probabilities are within 0.15 of each other
3. Email classified as Junk but contains any phishing-adjacent signal (urgency + account language, auth failure, suspicious URL, credential-adjacent phrasing)
4. BEC pattern detected — always flagged regardless of confidence (no links/attachments + executive impersonation + financial context)
5. AI-generated content indicators present combined with any phishing signal
6. Any high-weight signal present in an email otherwise classified as Junk
7. Attachment present from first-contact sender regardless of attachment type

---

## Edge Cases and Decision Rules

| Scenario | Classification | manual_review |
|---|---|---|
| Spam content + suspicious URL | Analyst Review | — |
| Legitimate domain + credential request in body | Phishing | true |
| No links, no attachments, urgency + financial request | Phishing (BEC) | true (always) |
| Newsletter + SPF fail | Analyst Review | — |
| First contact + perfect grammar + no signals | Analyst Review | — if any secondary signal present |
| SPF fail + DKIM fail + no other signals | Analyst Review | — |
| Known bulk sender + urgency language | Analyst Review | — |
| Lookalike domain + no other signals | Phishing | true |
| Reputable domain + DKIM fail only | Junk | — (unless other signals present) |
| Executable attachment from unknown sender | Phishing | true (always) |
| Open redirect on legitimate domain | Analyst Review/Phishing | — |

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
    │   ├─ URL signals (homograph, TLD, shortener flag, static pattern analysis)
    │   ├─ Attachment signals (type, name pattern)
    │   ├─ Sender–recipient relationship (first contact, domain familiarity)
    │   └─ Behavioral signals (off-hours, header anomalies, HTML obfuscation)
    │
    ├─ Run model inference (3-class: Spam / Junk / Phishing) → raw logits
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
    │   └─ SHAP on metadata MLP → feature contributions
    │
    └─ Final output: label + trust_score + risk_score + reasons[] + confidence_notes[]
           ↓
    Route: auto-folder / junk route / immediate alert / Analyst Review queue

    [Async — post-routing, delivered to analyst interface]
    ├─ Integrated Gradients on transformer → token attribution → rule summarizer phrases
    └─ PhishTank/SURBL cache lookup → URL threat intel enrichment
```
