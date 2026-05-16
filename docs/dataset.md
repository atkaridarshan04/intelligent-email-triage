# Dataset Strategy & Acquisition Plan

## Overview

Dataset quality is the single most critical determinant of model quality for this project.

The objective is not simply to collect a large number of email samples, but to construct a realistic, diverse, high-signal dataset suitable for AI-assisted SOC suspicious email triage.

Final classification target:

- **Spam**
- **Phishing**

Operational routing:

- **Analyst Review** for low-confidence predictions

This problem formulation intentionally simplifies the dataset challenge by focusing on the most operationally meaningful and realistically acquirable classes.

---

# Dataset Design Philosophy

The dataset must satisfy the following principles:

- realistic to acquire
- operationally relevant
- structurally informative
- semantically diverse
- resistant to shortcut learning
- compatible with heterogeneous public data formats
- reproducible
- scalable

The project explicitly avoids dependence on private enterprise telemetry.

---

# Core Challenge

There is no single public dataset that reliably provides:

- modern phishing email content
- realistic spam corpora
- enterprise metadata
- sender behavioral history
- infrastructure intelligence
- consistent formatting

Public datasets are distributed in highly inconsistent formats:

- CSV
- JSON
- text corpora
- phishing URL feeds
- parsed email dumps
- occasional raw `.eml`

As a result, the dataset strategy must prioritize normalization and enrichment rather than searching for a perfect unified corpus.

---

# Final Dataset Strategy

The adopted approach is:

## Hybrid Real-First Dataset Construction

```text
Real public datasets
        +
deterministic structural enrichment
        +
controlled synthetic augmentation
````

This ensures:

* real-world semantic grounding
* structural feature richness
* modern attack relevance
* manageable acquisition complexity

Synthetic data supplements gaps but does not dominate the corpus.

---

# Target Dataset Composition

Recommended target:

| Class    | Target Samples |
| -------- | -------------- |
| Spam     | 6,000–10,000   |
| Phishing | 8,000–12,000   |

Total target:

**14,000–22,000 samples**

Synthetic contribution:

**≤25%**

---

# Spam Dataset Strategy

## Definition

Spam refers to:

* unsolicited bulk communication
* promotional messaging
* nuisance mail
* low-risk unwanted communication

Examples:

* newsletters
* affiliate promotions
* ecommerce campaigns
* SaaS marketing emails
* crypto promotions
* coupon spam

Excluded:

* credential theft
* impersonation
* malware delivery
* fraudulent payment requests

---

# Real Spam Sources

## SpamAssassin Public Corpus

Use for:

* real spam email examples
* nuisance communication structure
* baseline spam diversity

Strengths:

* widely used benchmark corpus
* authentic spam samples
* structured email content

Limitations:

* older dataset

Still valuable as a foundational source.

---

## TREC Spam Track

Use for:

* large benchmark spam collections
* varied spam campaign structures
* bulk nuisance mail

Strengths:

* high volume
* diverse campaign patterns

Limitations:

* some historical bias

---

## Apache Spam Archives / Public Spam Dumps

Use for:

* real unsolicited promotional communication
* bulk spam structure diversity

Useful for expanding beyond benchmark datasets.

---

## Promotional Template Collection

Supplement with realistic modern promotional email templates.

Sources:

* SaaS marketing emails
* ecommerce newsletters
* affiliate campaigns
* promotional bulk messaging

Purpose:

improve modern realism.

---

# Synthetic Spam Augmentation

Synthetic spam is acceptable because nuisance promotional structure is comparatively easier to model.

Allowed synthetic categories:

* SaaS promotions
* ecommerce campaigns
* newsletters
* affiliate offers
* crypto marketing
* promotional bulk mail

Constraints:

* must remain non-malicious
* must not drift into phishing semantics
* must preserve realistic formatting diversity

---

# Phishing Dataset Strategy

## Definition

Phishing refers to malicious emails intended for:

* credential theft
* impersonation
* social engineering
* malware delivery
* invoice fraud
* payment fraud

Examples:

* Microsoft credential phishing
* fake security notifications
* payroll impersonation
* malicious invoice attachments
* fake MFA reset prompts

---

# Real Phishing Sources

## Nazario Phishing Corpus

Use for:

* real phishing email text
* phishing structure baselines
* malicious email semantics

Strengths:

* authentic phishing content
* directly relevant email examples

Limitations:

* older corpus

Still useful as seed data.

---

## PhishTank

Use for:

* verified phishing URLs
* campaign intelligence
* brand targeting signals

Purpose:

modern phishing infrastructure realism.

Strengths:

* continuously updated
* verified phishing intelligence

Limitation:

primarily URL-focused, not full email bodies.

Still highly valuable for enrichment.

---

## OpenPhish

Use for:

* active phishing infrastructure
* recent malicious URLs
* modern campaign patterns

Purpose:

improve temporal relevance.

Strengths:

* current phishing intelligence

Limitation:

not full email corpus.

Useful for URL-based enrichment and synthetic realism.

---

## CEAS / IWSPA Security Datasets

Use for:

* curated phishing research datasets
* structured security benchmark corpora

Strengths:

* higher curation quality
* research relevance

Preferred over low-quality random internet dumps.

---

## Curated GitHub Phishing Repositories

Use cautiously as supplementary sources.

Allowed only after:

* source validation
* deduplication
* normalization

Purpose:

expand campaign diversity.

---

# Synthetic Phishing Augmentation

Synthetic phishing should fill modern realism gaps rather than replace real malicious data.

Allowed scenarios:

* Microsoft 365 credential phishing
* Google Workspace credential theft
* Okta impersonation
* SharePoint phishing
* DocuSign impersonation
* payroll fraud
* invoice fraud
* MFA reset phishing

Requirements:

* polished language
* realistic enterprise tone
* subtle social engineering
* campaign diversity
* modern infrastructure realism

Avoid toy phishing generation.

Rejected examples:

```text
Dear user verify account immediately
```

Preferred realism:

```text
Your Microsoft 365 session requires reauthentication following recent policy enforcement.
```

---

# Structural Feature Enrichment Strategy

Public datasets are structurally inconsistent.

Many contain only:

* subject
* body
* label

To support multimodal learning, deterministic structural enrichment is applied.

---

# Sender Feature Enrichment

Derived features:

* display/from mismatch
* reply-to mismatch
* free-email sender usage

Purpose:

capture impersonation and sender inconsistency signals.

---

# URL Feature Enrichment

Derived features:

* URL count
* domain count
* shortened URL detection
* suspicious TLD detection
* IP literal URL detection
* URL entropy
* typosquatting similarity
* domain structure anomalies

Purpose:

capture phishing infrastructure characteristics.

---

# Attachment Feature Enrichment

Derived features:

* attachment presence
* archive detection
* executable detection
* macro-enabled document detection

Purpose:

capture malware delivery indicators.

---

# Statistical Text Enrichment

Derived features:

* subject length
* body length
* uppercase ratio
* digit ratio
* punctuation density
* link density
* special character ratio

Purpose:

capture structural communication patterns.

---

# Brand Impersonation Features

Derived features:

* known brand mention detection
* sender-brand mismatch
* impersonation consistency checks

Purpose:

capture common phishing impersonation strategies.

---

# Explicitly Rejected Data Dependencies

The dataset strategy intentionally excludes reliance on:

* SPF / DKIM / DMARC
* enterprise IP reputation feeds
* domain reputation subscriptions
* sender communication history
* analyst verdict telemetry
* enterprise communication graphs

Reason:

these are not reliably available in public datasets and would create unrealistic acquisition dependencies.

---

# Dataset Normalization Pipeline

All acquired sources are transformed into the canonical schema.

Supported inputs:

* CSV
* JSON
* parsed corpora
* raw `.eml`
* phishing feeds
* synthetic generators

Pipeline:

```text
Raw source
    ↓
Source adapter
    ↓
Canonical schema normalization
    ↓
Structural enrichment
    ↓
Training dataset
```

This ensures consistent model input despite heterogeneous origins.

---

# Leakage Prevention Strategy

Dataset leakage can create artificially inflated metrics.

Strict controls are mandatory.

---

## No Random Row Splitting

Never split randomly at email-row level.

Instead split by:

* phishing campaign
* template cluster
* domain family
* near-duplicate similarity groups

This prevents campaign memorization leakage.

---

## Deduplication

Remove:

* exact duplicates
* template clones
* repeated campaign variants

Required before training.

---

## Source Provenance Tracking

Every sample must retain:

* dataset source
* source type
* synthetic flag
* campaign grouping

This enables auditability and controlled splitting.

---

# Quality Gates Before Training

Training begins only when the following minimum criteria are met.

---

## Sample Volume

Minimum:

| Class    | Minimum |
| -------- | ------- |
| Spam     | 5,000   |
| Phishing | 6,000   |

---

## Campaign Diversity

Minimum:

**300+ unique phishing campaigns**

This matters more than raw sample count.

---

## Synthetic Ratio

Maximum:

**25%**

Synthetic data should augment, not dominate.

---

## Dataset Cleanliness

Required:

* deduplicated corpus
* stable labels
* campaign-aware split readiness

---

## Structural Coverage

Required:

majority of samples should support:

* URL features
* sender features
* text statistics

Sparse structural coverage weakens multimodal learning.

---

# Data Quality Philosophy

The objective is not:

> “largest possible dataset”

The objective is:

* realistic diversity
* clean supervision
* structural richness
* semantic relevance
* modern phishing realism
* robust generalization

A smaller clean dataset is significantly more valuable than a larger noisy one.
