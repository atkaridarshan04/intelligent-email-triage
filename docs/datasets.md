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

## Dataset Mapping to 4-Class Task

| Dataset | Spam | Gray | Phishing | Notes |
|---|---|---|---|---|
| SpamAssassin (spam) | ✓ | | | |
| SpamAssassin (hard ham) | | ✓ | | Hard ham ≈ gray |
| CEAS 2008 | ✓ | | | |
| TREC 2007 | ✓ | | | |
| Ling-Spam | ✓ | | | |
| Enron | | ✓ | | Legitimate corporate = gray/ham |
| Nazario Phishing | | | ✓ | |
| IWSPA-AP | | | ✓ | |
| Kaggle Phishing | | | ✓ | Verify quality |
| PhishTank | | | ✓ | URLs only |

**Note:** No public dataset natively labels "Junk" as a distinct class. Junk class training data must be constructed by:
1. Using "hard ham" from SpamAssassin
2. Using Enron emails as legitimate/gray examples
3. Manually curating a small set of newsletter/bulk mail examples
4. Using analyst-labeled data from the feedback loop over time

---

## Class Imbalance Considerations

Across all datasets combined, the approximate distribution is:
- Spam: ~60–70% of samples
- Legitimate/Gray: ~25–35% of samples
- Phishing: ~5–10% of samples

This imbalance must be addressed during training:
- **Oversample phishing** using SMOTE or data augmentation
- **Undersample spam** to balance training batches
- **Use focal loss** to focus learning on hard/minority examples
- **Stratified splits** for train/validation/test to maintain class ratios

---

## Data Preprocessing Notes

- Remove PII from email bodies before training (names, phone numbers, email addresses → placeholder tokens)
- Normalize URLs (decode percent-encoding, expand shortened URLs where possible)
- Strip email threading artifacts (quoted replies, forwarded headers) to focus on the original message
- Handle encoding issues (base64, quoted-printable) — decode to plain text before feature extraction
- For transformer models: truncate to model's max token length (512 for BERT-family), keeping subject + first N tokens of body

---

## Future Data Sources (Post-v1)

- Analyst-labeled emails from the feedback loop (most valuable long-term)
- Synthetic phishing generation using LLMs for data augmentation
- Updated PhishTank snapshots for URL model retraining
