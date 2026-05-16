# Phishing & Spam Attack Types

## Overview

This document defines the attack types this system is designed to detect and classify. These are the active threat patterns present in user-reported email queues. Every design decision in the classification logic and model architecture is grounded in handling these specific types.

---

## Attack Types We Detect

### 1. Spam

Unsolicited bulk email with no targeted malicious intent. Sent at scale for commercial or nuisance purposes.

**Characteristics:**
- Generic, non-personalized content
- Promotional or sensational language
- Links to commercial or low-reputation domains
- Sent from bulk mail infrastructure
- No credential requests, no impersonation, no financial fraud context

**Why it ends up in the analyst queue:** Users report it as suspicious because it looks unfamiliar or alarming. It is not a threat, but it creates noise.

**Detection approach:** Bulk messaging structure, promotional language patterns, absence of credential-request or impersonation signals, high URL count to commercial domains, unsubscribe link presence.

---

### 2. Credential Phishing

Mass or targeted emails designed to steal usernames and passwords by directing users to fake login pages.

**Characteristics:**
- Impersonates known brands (banks, Microsoft, Google, internal IT)
- Contains urgent language ("your account will be suspended")
- Links to lookalike domains or redirect chains ending at fake login pages
- Sender domain does not match the impersonated brand

**Detection approach:** Brand impersonation signals, URL structure analysis (typosquatting domains, suspicious TLDs, high entropy), urgency + credential-request combination, reply-to mismatch.

---

### 3. Spear Phishing

Targeted phishing using personalized content based on OSINT about the recipient — their name, role, company, colleagues.

**Characteristics:**
- Personalized greeting and context (name, job title, team references)
- Impersonates colleagues, IT teams, HR, or management
- Higher quality writing than mass phishing
- May or may not contain links — sometimes just requests action via reply

**Detection approach:** Sender structure analysis (display/From mismatch, free-email impersonation), internal role impersonation signals, brand impersonation with sender mismatch.

---

### 4. Business Email Compromise (BEC)

Pure social engineering — no links, no attachments. Impersonates executives or trusted partners to initiate financial fraud or sensitive data requests.

**Characteristics:**
- No malicious URLs or attachments
- Impersonates CEO, CFO, vendor, or legal team
- Requests wire transfers, gift cards, invoice changes, or sensitive data
- Exploits urgency and authority
- Often uses display name spoofing or free-email sender

**Why it's the hardest to detect:** No technical indicators. Looks identical to legitimate internal email. Cannot be caught by URL or attachment analysis alone.

**Detection approach:** Executive name detection in From/display fields, urgency + financial context combination, reply-to mismatch, free-email sender impersonating a corporate identity.

BEC will consistently trigger Analyst Review in early model versions due to limited technical indicators. This is expected and correct behavior.

---

### 5. Malware Delivery

Emails designed to deliver malicious payloads via attachments or malicious links.

**Characteristics:**
- Attachments: macro-enabled Office files, password-protected ZIPs, executables disguised as PDFs
- Links to malware hosting sites
- Often impersonates invoices, shipping notifications, HR documents
- Double extension abuse (e.g., `document.pdf.exe`)

**Detection approach:** Attachment type and naming patterns, executable and macro-enabled document detection, invoice/shipping impersonation signals.

---

### 6. AI-Generated Phishing

Phishing emails generated using LLMs — perfect grammar, contextual tone, personalized at scale. Bypasses traditional grammar and style-based heuristics entirely.

**Characteristics:**
- No spelling or grammar errors
- Contextually appropriate tone and phrasing
- Can mimic writing style of known contacts
- Indistinguishable from legitimate email on surface-level analysis

**Why it matters:** Traditional detection relies partly on poor writing quality as a signal. AI-generated phishing removes that signal entirely.

**Detection approach:** Structural signals (sender mismatch, suspicious URL structure, attachment indicators), semantic intent analysis (what is this email trying to get the user to do?), brand impersonation signals.

---

### 7. Multi-Stage / Redirect Phishing

Phishing that uses redirect chains to obscure the final malicious destination. The initial URL in the email may appear legitimate.

**Characteristics:**
- Email contains a link to a legitimate or neutral site
- That site redirects to the phishing page
- May involve URL shorteners or legitimate cloud services as intermediaries
- Used to bypass URL reputation checks that only inspect the first URL

**Detection approach:** URL shortener detection, suspicious TLD analysis, high URL entropy, domain structure anomalies.

---

## Signal Summary by Attack Type

| Attack Type | Key Signals |
|---|---|
| Spam | Bulk structure, promotional language, no credential request, high URL count to commercial domains |
| Credential Phishing | Brand impersonation, typosquatting domain, urgency + credential request, reply-to mismatch |
| Spear Phishing | Display/From mismatch, internal role impersonation, free-email sender, brand mismatch |
| BEC | No links/attachments, executive impersonation, financial context, reply-to mismatch |
| Malware Delivery | Executable/macro attachment, invoice/shipping impersonation, double extension |
| AI-Generated | Structural signals, sender mismatch, semantic intent (no style errors to rely on) |
| Multi-Stage Redirect | URL shorteners, suspicious TLD, high URL entropy, domain structure anomalies |

---

## Scope Note

This system classifies emails into two output buckets: **Spam** and **Phishing**. The attack types above map as follows:

- Spam → Spam
- Credential Phishing, Spear Phishing, BEC, Malware Delivery, AI-Generated, Multi-Stage Redirect → Phishing

BEC and AI-generated phishing will consistently trigger Analyst Review in early model versions due to limited technical indicators. This is expected and correct behavior — the system routes uncertain cases to humans rather than forcing incorrect automated decisions.
