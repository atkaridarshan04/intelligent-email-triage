# Phishing & Spam Attack Types

## Overview

This document defines the attack types this system is designed to detect and classify. These are not historical categories — they are the active threat patterns present in user-reported email queues today. Every design decision in the classification logic and AI model is grounded in handling these specific types.

---

## Attack Types We Detect

### 1. Spam / Junk

Unsolicited bulk email with no targeted malicious intent. Sent at scale, typically for commercial or nuisance purposes.

**Characteristics:**
- Generic, non-personalized content
- Promotional or sensational language
- Links to commercial or low-reputation domains
- Sent from bulk mail infrastructure
- Often passes SPF but lacks DKIM/DMARC

**Why it ends up in the analyst queue:** Users report it as suspicious because it looks unfamiliar or alarming. It is not a threat, but it creates noise.

**Detection approach:** High-volume sender patterns, bulk mail infrastructure signals, absence of credential-request or impersonation signals, known bulk sender domains.

---

### 2. Bulk / Gray Email

Email from a legitimate or semi-legitimate sender that the recipient didn't explicitly request. Ambiguous by nature — not clearly malicious, not clearly safe.

**Characteristics:**
- Newsletters, marketing campaigns, automated notifications
- Sent from real domains with valid authentication
- No explicit malicious intent but may contain account-related language
- Recipient has no prior relationship with sender

**Why it ends up in the analyst queue:** Looks suspicious to users because it's unexpected or uses account-related language. Legitimate but unrequested.

**Detection approach:** Sender domain reputation, authentication results, content tone (promotional vs. threatening), absence of credential-request signals, unsubscribe link presence.

---

### 3. Credential Phishing

Mass or targeted emails designed to steal usernames and passwords by directing users to fake login pages.

**Characteristics:**
- Impersonates known brands (banks, Microsoft, Google, internal IT)
- Contains urgent language ("your account will be suspended")
- Links to lookalike domains or redirect chains ending at fake login pages
- Often fails SPF/DKIM/DMARC or uses newly registered domains

**Detection approach:** Brand impersonation signals, URL structure analysis (lookalike domains, redirect chains), authentication failures, urgency + credential-request combination.

---

### 4. Spear Phishing

Targeted phishing using personalized content based on OSINT about the recipient — their name, role, company, colleagues.

**Characteristics:**
- Personalized greeting and context (name, job title, team references)
- Impersonates colleagues, IT teams, HR, or management
- Higher quality writing than mass phishing
- May or may not contain links — sometimes just requests action via reply

**Detection approach:** Sender–recipient relationship analysis (first contact from this domain?), personalization anomaly detection, impersonation of internal roles, domain spoofing signals.

---

### 5. Business Email Compromise (BEC)

Pure social engineering — no links, no attachments. Impersonates executives or trusted partners to initiate financial fraud or sensitive data requests.

**Characteristics:**
- No malicious URLs or attachments
- Impersonates CEO, CFO, vendor, or legal team
- Requests wire transfers, gift cards, invoice changes, or sensitive data
- Exploits urgency and authority
- Often uses display name spoofing or lookalike domains

**Why it's the hardest to detect:** No technical indicators. Looks identical to legitimate internal email. Cannot be caught by URL or attachment scanners.

**Detection approach:** Executive name detection in From/display fields, urgency + financial context combination, sender–recipient history (has this "executive" emailed this person before?), domain spoofing signals, reply-to mismatch.

---

### 6. Malware Delivery

Emails designed to deliver malicious payloads via attachments or drive-by download links.

**Characteristics:**
- Attachments: macro-enabled Office files, password-protected ZIPs, executables disguised as PDFs
- Links to malware hosting sites or exploit kits
- Often impersonates invoices, shipping notifications, HR documents
- May use multi-stage delivery (link → download → execution)

**Detection approach:** Attachment type and naming patterns, URL reputation, file extension mismatches, invoice/shipping impersonation signals, known malware delivery infrastructure.

---

### 7. AI-Generated Phishing

Phishing emails generated using LLMs — perfect grammar, contextual tone, personalized at scale. Bypasses traditional grammar and style-based heuristics entirely.

**Characteristics:**
- No spelling or grammar errors
- Contextually appropriate tone and phrasing
- Can mimic writing style of known contacts
- Indistinguishable from legitimate email on surface-level analysis

**Why it matters:** Traditional detection relies partly on poor writing quality as a signal. AI-generated phishing removes that signal entirely.

**Detection approach:** Infrastructure signals (domain age, IP reputation, auth failures), sender–recipient relationship, semantic intent analysis (what is this email trying to get the user to do?), behavioral anomalies.

---

### 8. Multi-Stage / Redirect Phishing

Phishing that uses redirect chains to obscure the final malicious destination. The initial URL in the email may appear legitimate.

**Characteristics:**
- Email contains a link to a legitimate or neutral site
- That site redirects (via JavaScript, meta refresh, or open redirect) to the phishing page
- Used to bypass URL reputation checks that only inspect the first URL
- May involve URL shorteners, legitimate cloud services (Google Docs, OneDrive) as intermediaries

**Detection approach:** Redirect chain analysis, final destination URL inspection, open redirect detection on known legitimate domains, URL shortener expansion.

---

## Signal Summary by Attack Type

| Attack Type | Key Signals |
|---|---|
| Spam | Bulk infrastructure, no personalization, commercial links, no auth failures |
| Gray / Bulk | Legitimate domain, valid auth, promotional tone, no credential request |
| Credential Phishing | Brand impersonation, auth failures, lookalike domain, urgency + credential request |
| Spear Phishing | First-contact sender, personalization, internal role impersonation, domain spoofing |
| BEC | No links/attachments, executive impersonation, financial context, reply-to mismatch |
| Malware Delivery | Suspicious attachments, malware hosting URLs, invoice/shipping impersonation |
| AI-Generated | Infrastructure signals, sender–recipient anomaly, semantic intent (no style errors) |
| Multi-Stage Redirect | Redirect chains, open redirects, URL shorteners, final destination mismatch |

---

## Scope Note

This system classifies emails into three output buckets: **spam**, **gray**, and **phishing**. The attack types above map to those buckets as follows:

- Spam → Spam bucket
- Gray / Bulk → Gray bucket
- Credential Phishing, Spear Phishing, BEC, Malware Delivery, AI-Generated, Multi-Stage Redirect → Phishing bucket

BEC and AI-generated phishing will consistently trigger the `manual_review` flag in early model versions due to limited technical indicators. This is expected and correct behavior.
