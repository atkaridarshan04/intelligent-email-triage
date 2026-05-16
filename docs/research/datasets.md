# Public Datasets for Training and Validation

## Overview

All training and validation data comes from publicly available datasets. This document lists the datasets used, their characteristics, and how they map to the binary classification task (Spam / Phishing).

No proprietary, organization-internal, or internet-scraped data is used.

---

## Dataset Strategy

There is no single public dataset that reliably provides modern phishing email content, realistic spam corpora, and consistent formatting. Public datasets are distributed in highly inconsistent formats — CSV, JSON, text corpora, phishing URL feeds, parsed email dumps, occasional raw `.eml`.

The adopted approach is **hybrid real-first dataset construction**:

```
Real public datasets
        +
deterministic structural enrichment
        +
controlled synthetic augmentation (≤ 25% of total)
```

This ensures real-world semantic grounding, structural feature richness, and modern attack relevance.

---

## Target Dataset Composition

| Class | Target Samples |
|---|---|
| Spam | 6,000–10,000 |
| Phishing | 8,000–12,000 |

Total target: **14,000–22,000 samples**

Synthetic contribution: **≤ 25%**

---

## Spam Datasets

### SpamAssassin Public Corpus
- **Type:** Spam / Ham
- **Size:** ~6,000 emails
- **Source:** Apache SpamAssassin project
- **URL:** https://spamassassin.apache.org/old/publiccorpus/
- **Use:** Spam class training — real spam examples, nuisance communication structure, baseline spam diversity
- **Notes:** Widely used benchmark corpus; authentic spam samples

---

### TREC 2007 Spam Track
- **Type:** Spam / Ham
- **Size:** ~75,000 emails
- **Source:** TREC (Text REtrieval Conference)
- **Use:** Spam class training — large benchmark collection, varied spam campaign structures
- **Notes:** High volume; chronological ordering useful for temporal evaluation

---

### CEAS 2008 Spam Corpus
- **Type:** Spam / Ham
- **Size:** ~40,000 emails
- **Source:** CEAS (Conference on Email and Anti-Spam)
- **Use:** Spam class training — additional volume and stylistic diversity
- **Notes:** Older dataset; useful for foundational spam patterns

---

## Phishing Datasets

### Nazario Phishing Corpus
- **Type:** Phishing
- **Size:** ~2,000+ phishing emails
- **Source:** Jose Nazario's phishing corpus (academic mirrors)
- **Use:** Phishing class training — real phishing email text, phishing structure baselines
- **Notes:** One of the most cited phishing datasets; covers credential phishing and brand impersonation

---

### IWSPA-AP 2018 Phishing Dataset
- **Type:** Phishing / Legitimate
- **Source:** IWSPA (International Workshop on Security and Privacy Analytics)
- **Use:** Phishing class training — includes spear phishing samples underrepresented elsewhere
- **Notes:** Specifically designed for ML-based phishing detection research; higher curation quality

---

### PhishTank
- **Type:** Phishing URLs
- **Source:** PhishTank community (OpenDNS)
- **URL:** https://www.phishtank.com/developer_info.php
- **Use:** URL feature enrichment — verified phishing URLs for URL-based feature validation and synthetic sample construction
- **Notes:** Continuously updated; verified phishing intelligence. URL-focused, not full email bodies. Queried at dataset construction time and cached — no live calls at inference time.

---

### OpenPhish
- **Type:** Active phishing URLs
- **Source:** OpenPhish
- **Use:** URL feature enrichment — recent malicious URLs, modern campaign patterns
- **Notes:** Current phishing intelligence; useful for improving temporal relevance of URL features

---

### Phishing Email Dataset (Kaggle)
- **Type:** Phishing / Safe
- **Source:** Kaggle community datasets
- **URL:** https://www.kaggle.com/datasets/naserabdullahalam/phishing-email-dataset
- **Use:** Phishing class training after quality validation
- **Notes:** Community datasets vary in reliability. Use only after a 500-sample quality audit (Cohen's Kappa ≥ 0.70 against Nazario/IWSPA-AP label definitions). If audit fails, exclude entirely.

---

## Dataset Mapping to Binary Task

| Dataset | Spam | Phishing | Notes |
|---|---|---|---|
| SpamAssassin (spam) | ✓ | | |
| TREC 2007 | ✓ | | |
| CEAS 2008 | ✓ | | |
| Nazario Phishing | | ✓ | |
| IWSPA-AP | | ✓ | |
| Kaggle Phishing | | ✓ | Verify label quality before use |
| PhishTank | | ✓ | URLs only — enrichment and synthetic construction |
| OpenPhish | | ✓ | URLs only — enrichment |

---

## Synthetic Augmentation

### Spam Augmentation

Synthetic spam is acceptable because nuisance promotional structure is comparatively easier to model.

Allowed categories:
- SaaS promotions
- Ecommerce campaigns
- Newsletters
- Affiliate offers
- Promotional bulk mail

Constraints: must remain non-malicious, must not drift into phishing semantics, must preserve realistic formatting diversity.

### Phishing Augmentation

Synthetic phishing fills modern realism gaps rather than replacing real malicious data.

Allowed scenarios:
- Microsoft 365 credential phishing
- Google Workspace credential theft
- Okta impersonation
- SharePoint phishing
- DocuSign impersonation
- Payroll fraud
- Invoice fraud
- MFA reset phishing

Requirements: polished language, realistic enterprise tone, subtle social engineering, campaign diversity, modern infrastructure realism.

Avoid toy phishing generation. Rejected:
```
Dear user verify account immediately
```

Preferred realism:
```
Your Microsoft 365 session requires reauthentication following recent policy enforcement.
```

---

## Structural Feature Enrichment

Public datasets are structurally inconsistent — many contain only subject, body, and label. To support multimodal learning, deterministic structural enrichment is applied at dataset construction time.

### Sender Features
- Display/From mismatch
- Reply-to mismatch
- Free-email sender usage

### URL Features
- URL count, domain count
- Shortened URL detection
- Suspicious TLD detection
- IP literal URL detection
- URL entropy
- Typosquatting similarity (edit distance against known brand domains, with Unicode normalization)
- Domain structure anomalies

### Attachment Features
- Attachment presence
- Archive detection
- Executable detection
- Macro-enabled document detection

### Statistical Text Features
- Subject length, body length
- Uppercase ratio, digit ratio
- Punctuation density, link density

### Brand Impersonation Features
- Known brand mention detection
- Sender-brand mismatch

---

## Explicitly Rejected Data Dependencies

The dataset strategy intentionally excludes:

- SPF / DKIM / DMARC results
- Enterprise IP reputation feeds
- Domain reputation subscriptions
- Sender communication history
- Analyst verdict telemetry

These are not reliably available in public datasets and would create unrealistic acquisition dependencies.

---

## Leakage Prevention

### No Random Row Splitting

Never split randomly at email-row level. Split by phishing campaign, template cluster, or near-duplicate similarity groups to prevent campaign memorization leakage.

### Deduplication

Remove exact duplicates, template clones, and repeated campaign variants before training. Hash on `sha256(subject + body_text[:500])`; use MinHash LSH (Jaccard ~0.85) for near-duplicates.

### Source Provenance Tracking

Every sample retains: dataset source, source type, synthetic flag, campaign grouping. This enables auditability and controlled splitting.

---

## Quality Gates Before Training

| Gate | Minimum |
|---|---|
| Spam samples | 5,000 |
| Phishing samples | 6,000 |
| Unique phishing campaigns | 300+ |
| Synthetic ratio | ≤ 25% |
| Structural coverage | Majority of samples support URL, sender, and text stat features |

A smaller clean dataset is significantly more valuable than a larger noisy one.
