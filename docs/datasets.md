# Public Datasets for Training and Validation

## Overview

All training and validation data must come from publicly available datasets. This document lists the datasets available, their characteristics, and how they map to the 4-class classification task.

No proprietary, organization-internal, or internet-scraped data is used.

---

## Primary Datasets

### 1. CEAS 2008 Spam Corpus
- **Type:** Spam / Ham (legitimate)
- **Size:** ~40,000 emails
- **Source:** CEAS (Conference on Email and Anti-Spam) shared task
- **Use:** Spam bucket training, spam vs. legitimate baseline
- **Notes:** Older dataset — useful for foundational spam patterns but may not reflect modern spam

---

### 2. SpamAssassin Public Corpus
- **Type:** Spam / Ham
- **Size:** ~6,000 emails (easy and hard ham, spam)
- **Source:** Apache SpamAssassin project
- **URL:** https://spamassassin.apache.org/old/publiccorpus/
- **Use:** Spam bucket training, includes "hard ham" which maps well to the Junk class
- **Notes:** The "hard ham" category (legitimate emails that look like spam) is directly useful for Junk class training

---

### 3. Enron Email Dataset
- **Type:** Legitimate corporate email (ham)
- **Size:** ~500,000 emails from ~150 users
- **Source:** FERC investigation, made public
- **URL:** https://www.cs.cmu.edu/~enron/
- **Use:** Legitimate email baseline, sender–recipient relationship modeling, Junk class negative examples
- **Notes:** Real corporate email — valuable for modeling normal communication patterns

---

### 4. Nazario Phishing Corpus
- **Type:** Phishing
- **Size:** ~2,000+ phishing emails
- **Source:** Jose Nazario's phishing corpus (hosted on various academic mirrors)
- **Use:** Phishing bucket training
- **Notes:** One of the most cited phishing datasets; covers credential phishing, brand impersonation

---

### 5. PhishTank
- **Type:** Phishing URLs
- **Source:** PhishTank community (OpenDNS)
- **URL:** https://www.phishtank.com/developer_info.php
- **Use:** URL feature training — known phishing URLs for URL-specific model
- **Notes:** Updated regularly; provides verified phishing URLs with metadata

---

### 6. TREC 2007 Spam Track
- **Type:** Spam / Ham
- **Size:** ~75,000 emails
- **Source:** TREC (Text REtrieval Conference)
- **Use:** Spam bucket training, large-scale evaluation
- **Notes:** Well-structured for ML evaluation; includes chronological ordering useful for concept drift testing

---

### 7. Ling-Spam Dataset
- **Type:** Spam / Legitimate (linguistics mailing list)
- **Size:** ~2,893 emails
- **Source:** Academic dataset (Androutsopoulos et al.)
- **Use:** Spam classification baseline, text feature evaluation
- **Notes:** Small but clean; good for quick model validation

---

### 8. UCI SMS Spam Collection
- **Type:** SMS Spam / Ham
- **Source:** UCI Machine Learning Repository
- **URL:** https://archive.ics.uci.edu/ml/datasets/SMS+Spam+Collection
- **Use:** Supplementary — short-text spam patterns transferable to email subject lines
- **Notes:** SMS context differs from email but subject-line spam patterns overlap

---

### 9. IWSPA-AP 2018 Phishing Dataset
- **Type:** Phishing / Legitimate
- **Source:** IWSPA (International Workshop on Security and Privacy Analytics)
- **Use:** Phishing detection, includes spear phishing samples
- **Notes:** Specifically designed for ML-based phishing detection research

---

### 10. Phishing Email Dataset (Kaggle)
- **Type:** Phishing / Safe
- **Source:** Kaggle community datasets (multiple contributors)
- **URL:** https://www.kaggle.com/datasets/naserabdullahalam/phishing-email-dataset
- **Use:** Phishing bucket training, quick prototyping
- **Notes:** Verify label quality before use — community datasets vary in reliability


---

### 11. PhiUSIIL Phishing URL Dataset
- **Type:** Phishing / Legitimate URLs
- **Source:** Academic dataset (PhiUSIIL)
- **Use:** URL feature training — phishing URL detection
- **Notes:** Large-scale dataset specifically designed for phishing URL classification; complements PhishTank

---

## Dataset Mapping to 3-Class Task

| Dataset | Spam | Junk | Phishing | Notes |
|---|---|---|---|---|
| SpamAssassin (spam) | ✓ | | | |
| SpamAssassin (hard ham) | | ✓ | | Promotional/newsletter-like samples re-labeled as Junk candidates |
| CEAS 2008 | ✓ | | | |
| TREC 2007 | ✓ | | | |
| Ling-Spam | ✓ | | | |
| Enron (external non-business) | | ✓ | | Event invites, unsolicited services, mailing list clutter |
| Nazario Phishing | | | ✓ | |
| IWSPA-AP | | | ✓ | |
| Kaggle Phishing | | | ✓ | Verify label quality |
| PhishTank | | | ✓ | URLs only — local cache, no live calls at inference |

---

## Junk Class Construction Strategy

No public dataset natively labels Junk as a distinct class. The Junk class is bootstrapped through **weak supervision + manual curation + rule filtering** across five sources:

**Source A — Public spam corpora re-labeled subset**
Selected records from SpamAssassin, CEAS, TREC, Ling-Spam that are promotional, solicitation-heavy, newsletter-like, or repetitive marketing style — with no credential theft orientation. These become Junk candidates.

**Source B — Enron external non-business noise**
Non-core external mails from the Enron corpus: event invites, unsolicited services, generic advertisements, mailing list clutter.

**Source C — Synthetic Junk generation**
Realistic nuisance emails generated from templates (e.g., "Limited-time consulting opportunity", "Exclusive webinar invitation", "Claim your reward points"). Generated with varied sender names, mild urgency, generic offers, harmless links.

Synthetic samples are **treated as candidate data, not trusted data.** All synthetic samples must pass the same exclusion filters as organic Junk data and are included in the same human validation pool before entering training.

**Source D — Public newsletter / marketing samples**
Retail newsletters, webinar campaigns, B2B vendor outreach, SaaS promotions from publicly available opt-in promotional mail examples.

**Source E — Manual curated gold set**
500–1,000 manually reviewed Junk emails. This is the validation anchor for the full Junk dataset.

### Junk Labeling Rules

An email is labeled Junk if it satisfies **at least 2 of**:
- Promotional / sales intent
- Bulk marketing style
- Irrelevant solicitation
- Low sender trust
- Misleading clickbait language
- Generic urgency

And **must NOT contain**:
- Credential harvesting request
- Payment change or wire transfer request
- Login / verification prompt
- Impersonation of a known brand or executive
- Malware attachment or lure
- Urgent account suspension language

If any phishing indicator is present, the label moves to Phishing — not Junk.

### Junk Quality Validation

Randomly sample 500 Junk labels (including synthetic samples). Two independent reviewers classify each as Junk / Spam / Phishing / Legitimate.

Target: **inter-rater agreement (Cohen's Kappa) > 0.75** before training proceeds.

### Junk Promotion to Learned Class

The Junk class will be promoted from weak-supervision construction to a fully learned class once the feedback loop has accumulated **≥5,000 analyst-verified Junk labels** with Cohen's Kappa > 0.75 across reviewers.

### Target Dataset Size

| Class | Target Count |
|---|---|
| Spam | ~20,000 |
| Junk | ~15,000 |
| Phishing | ~20,000 |

Counts are targets, not hard limits. Final composition is governed by stratification rules below.

---

## Stratification and Sampling Rules

Raw sample counts alone do not guarantee a useful training set. Dataset composition must be balanced across three dimensions:

**Time periods:**
- Legacy era (pre-2010 corpora)
- Mid era (2010–2018)
- Recent samples (2018–present, including modern phishing patterns)

**Phishing attack subtypes** (phishing class must cover all):
- Credential harvesting
- BEC / executive impersonation
- Malware delivery
- Invoice / payment fraud
- Redirect / landing-page phishing

**Spam / Junk styles** (spam and junk classes must cover all):
- Newsletters and marketing
- B2B outreach and promotions
- Scams without credential theft
- Bulk nuisance mail
- Event invites and solicitations

### Sampling Manifest

A sampling manifest is generated at dataset construction time, recording for every training sample:
- Source dataset
- Era bucket (legacy / mid / recent)
- Attack subtype or content style
- Assigned label

The manifest is versioned alongside the model checkpoint. This makes dataset composition fully reproducible and auditable.

---

## Class Imbalance Considerations

Across all datasets combined, the approximate raw distribution is:
- Spam: ~60–70% of samples
- Junk (constructed): ~10–15% of samples
- Phishing: ~5–10% of samples

This imbalance must be addressed during training:
- **Oversample phishing** using SMOTE or data augmentation
- **Undersample spam** to balance training batches
- **Use focal loss** to focus learning on hard/minority examples
- **Stratified splits** for train/validation/test to maintain class ratios

Final training composition targets: Spam ~20k / Junk ~15k / Phishing ~20k — governed by stratification rules, not raw counts alone.

---

## Data Preprocessing Notes

- Remove PII from email bodies before training (names, phone numbers, email addresses → placeholder tokens)
- Normalize URLs (decode percent-encoding; do not expand shortened URLs inline — URL shortener presence is treated as a signal)
- Strip email threading artifacts (quoted replies, forwarded headers) to focus on the original message
- Handle encoding issues (base64, quoted-printable) — decode to plain text before feature extraction
- Apply Unicode normalization before homograph detection — edit distance alone does not catch Cyrillic/Latin lookalike substitutions
- For transformer models: truncate to model's max token length (512 for BERT-family), keeping subject + first N tokens of body

---

## Future Data Sources (Post-v1)

- Analyst-labeled emails from the feedback loop (most valuable long-term)
- Synthetic phishing generation using LLMs for data augmentation
- Updated PhishTank snapshots for URL model retraining
