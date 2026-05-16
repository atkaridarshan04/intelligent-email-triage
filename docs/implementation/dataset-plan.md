# Dataset Construction Plan

## The Core Problem

The datasets listed in `docs/research/datasets.md` identify the right sources. What must be resolved is **how much to use from each, in what form, and why** — given two constraints that pull against each other:

1. Phishing samples are rare in public datasets (~5–10% of raw data), but the model needs >98% phishing recall
2. Most public datasets are old (pre-2015), but the model needs to generalize to modern attack patterns

Every decision below is driven by those two constraints.

---

## Dataset Selection: What to Use and Why

### Spam Class

**Use: TREC 2007 (~75k) + SpamAssassin spam partition (~3k) + CEAS 2008 (~40k)**

TREC 2007 is the backbone — largest, best-structured, and has chronological ordering essential for temporal evaluation. CEAS 2008 adds volume and stylistic diversity. SpamAssassin spam is small but high-quality and well-curated.

**Raw spam available: ~118k samples. Target: ~6,000–10,000 after stratified downsampling.**

Using all 118k would require proportionally inflating phishing to match (which doesn't exist in public data) or training on a severely imbalanced set. The target range is enough to learn spam patterns thoroughly while keeping the training set balanced.

Downsampling strategy: stratify by era (legacy/mid/recent) and spam style (marketing, scam, bulk, newsletter). Don't take the first N samples — that over-represents the oldest data.

---

### Phishing Class

**Use: Nazario (~2k) + IWSPA-AP + Kaggle Phishing (after quality filtering)**

Total organic phishing data from public sources is roughly 5,000–8,000 samples after deduplication and quality filtering. That's not enough for the 8,000–12,000 target.

**Nazario** is the most cited and most reliable. Use all of it.

**IWSPA-AP** is specifically designed for ML phishing detection and includes spear phishing — a subtype underrepresented elsewhere. Use all of it.

**Kaggle Phishing**: Use only after a mandatory quality gate — cross-check a random 500-sample audit against Nazario/IWSPA-AP label definitions. If Cohen's Kappa < 0.70, exclude entirely. If it passes, use the verified portion.

**The gap problem**: Even with all organic sources, you'll have ~5–8k phishing samples. The target requires augmentation.

**Augmentation strategy for phishing:**

1. **Template-based text augmentation** — take real phishing emails and apply controlled perturbations: synonym substitution in non-signal phrases, sender name variation, brand name swapping (PayPal → Amazon → Microsoft), subject line paraphrasing. Preserves the semantic phishing signal while increasing surface diversity.

2. **Explicit metadata assignment for augmented samples** — every augmented sample must have structured features explicitly assigned, not inherited blindly from the source. Template-generated samples get: `reply_to_mismatch=True`, `sender_domain_age_days=1–30`, `free_email_sender=True` (where applicable).

**Subtype coverage requirement**: Phishing samples must cover all major subtypes:
- Credential harvesting
- BEC / executive impersonation
- Malware delivery
- Invoice / payment fraud
- Redirect / landing-page phishing

BEC is the hardest — it has no links, no attachments, and relies purely on text signals. BEC template augmentation must cover all sub-patterns:
- Executive impersonation + wire transfer request
- Executive impersonation + gift card request
- Executive impersonation + invoice/payment change
- Vendor impersonation + bank account change
- HR impersonation + payroll redirect

Each sub-pattern needs at least 200–300 samples. BEC will still route to Analyst Review in v1 regardless of confidence — but the model needs enough BEC signal to recognize the pattern at all.

---

## Final Composition Targets

| Class | Organic Sources | Augmented/Synthetic | Total Target |
|---|---|---|---|
| Spam | ~118k available → downsample | None needed | 6,000–10,000 |
| Phishing | ~5,000–8,000 organic | Fill to target | 8,000–12,000 |
| **Total** | | | **14,000–22,000** |

Synthetic contribution must not exceed 25% of total samples.

Quality and diversity matter more than raw count. A 14k dataset stratified across eras, sources, and subtypes produces a better model than a 100k dataset dominated by legacy spam from 2007.

---

## Stratification: The Most Important Rule

Raw counts don't guarantee generalization. The sampling manifest must enforce:

**Era distribution (per class):**
- Legacy (pre-2010): ≤ 30% of any class
- Mid (2010–2018): ~40%
- Recent (2018–present): ≥ 30%

Most public datasets are legacy or mid-era. Recent samples are scarce. This is where synthetic augmentation and PhishTank (continuously updated) become critical for the phishing class. For spam, TREC 2007 is legacy but large — cap its contribution at 30% of the spam class.

**Phishing subtype distribution:**
Each major subtype should represent at least 10% of the phishing class. BEC will be the hardest to hit — accept 8–10% for BEC in v1 and compensate with the always-route-to-review rule.

**Source diversity:**
No single dataset should contribute more than 40% of any class. This prevents the model from learning dataset-specific artifacts instead of generalizable signals.

---

## What Not to Use

**UCI SMS Spam**: Wrong modality. No headers, no HTML, no URL structure. Would teach the model SMS-specific patterns that actively hurt email classification.

**Raw PhishTank as training emails**: PhishTank provides URLs, not full emails. Use it to enrich existing phishing samples and validate URL features, not as standalone training data.

**Unaudited Kaggle data**: Only use after the 500-sample quality audit passes the Kappa threshold. Label noise in the phishing class directly degrades recall — fewer clean samples is better than more noisy ones.

---

## Train / Validation / Test Split

70% / 15% / 15%, stratified by class. Additional constraint: **the test set should be temporally later than the training set where timestamps are available.** This is more realistic than a random split — in production, the model always sees future emails it wasn't trained on.

---

## The Sampling Manifest

Every training sample gets a record in the manifest:

```
source | era_bucket | subtype | label | augmented (bool) | split (train/val/test)
```

This is versioned with the model checkpoint. If a model version shows degraded phishing recall, you can inspect the manifest to see if a particular era bucket or subtype is underrepresented. Without the manifest, debugging dataset composition issues is guesswork.

---

# Feature Extraction Plan

## What the Model Consumes Per Email

### Text Encoder Input
Subject + body → tokenized → RoBERTa embeddings. Covered by existing email corpora.

### Structured Feature Encoder Input

| Feature | Source | Availability |
|---|---|---|
| Display/From mismatch | `From` header display name vs. address | Directly derivable |
| Reply-to mismatch | `Reply-To` vs `From` domain | Directly derivable if headers preserved |
| Free-email sender | `From` domain against known free-email providers | Directly derivable |
| URL count | Parse HTML/text body | Directly derivable |
| Domain count | Extract unique domains from URLs | Directly derivable |
| Shortened URL presence | Pattern match against known shortener domains | Directly derivable |
| Suspicious TLD | Extract TLD from URL domains | Derivable with static lookup table |
| IP literal URL | Regex on URL host | Directly derivable |
| URL entropy | Shannon entropy of URL domain | Directly derivable |
| Typosquatting similarity | Edit distance against brand domain list | Derivable with static brand list |
| Attachment presence | MIME structure | Directly derivable |
| Attachment type | MIME type declared in headers | Directly derivable |
| Executable/macro detection | MIME type + filename extension | Directly derivable |
| Subject length | Character count | Directly derivable |
| Body length | Character count | Directly derivable |
| Uppercase ratio | Character analysis | Directly derivable |
| Punctuation density | Character analysis | Directly derivable |
| Link density | Link count / word count | Directly derivable |
| Brand mention | Pattern match against brand name list | Derivable with static brand list |
| Sender-brand mismatch | Brand mention vs. sender domain | Derivable |

All features are deterministically derivable from email content. No enterprise telemetry required.

---

## Typosquatting Detection

Computed at feature extraction time:
- Levenshtein edit distance ≤ 2 against a list of ~500 known brand domains (Microsoft, PayPal, Amazon, Google, Apple, Chase, etc.)
- Unicode normalization before edit distance computation — edit distance alone does not catch Cyrillic/Latin lookalike substitutions (e.g., Cyrillic `а` → Latin `a`)
- Subdomain abuse detection: check if a known brand domain appears as a subdomain of the sender domain (e.g., `paypal.com.attacker.net`)

The brand domain list is a static versioned asset.

---

## TLD Risk Score

A static lookup table mapping TLDs to a risk tier:

- High risk (score 3): `.xyz`, `.top`, `.tk`, `.ml`, `.ga`, `.click`, `.gq`, `.cf` — free TLDs heavily abused for phishing infrastructure
- Medium risk (score 2): `.info`, `.biz`, `.online`, `.site`, `.website`
- Low risk (score 1): `.com`, `.org`, `.net`, `.edu`, `.gov`, `.co.uk`, `.de`, `.fr`

---

## Complete Feature Vector Per Training Sample

Every training sample must have all of the following populated before training begins:

**Text features** (transformer input):
`subject`, `body_text`

**Structured features** (MLP input):
`display_from_mismatch`, `reply_to_mismatch`, `free_email_sender`, `url_count`, `domain_count`, `shortened_url_present`, `suspicious_tld_present`, `ip_literal_url`, `url_entropy`, `typosquatting_detected`, `has_attachment`, `attachment_type`, `executable_detected`, `macro_detected`, `subject_length`, `body_length`, `uppercase_ratio`, `punctuation_density`, `link_density`, `brand_mention`, `sender_brand_mismatch`

**Label**: `spam` | `phishing`

**Manifest fields**: `source`, `era_bucket`, `subtype`, `label`, `augmented`, `split`

Any sample missing more than 2 structured features after extraction is excluded from training. Imputing zeros for missing features introduces systematic bias.

---

## Dataset Construction Order

1. Download all raw corpora (TREC, SpamAssassin, CEAS, Nazario, IWSPA-AP, Kaggle)
2. Parse all emails: extract headers, body text, MIME structure, URLs
3. **Run cross-dataset deduplication** — hash on `sha256(subject + body_text[:500])`; use MinHash LSH (Jaccard ~0.85) for near-duplicates; on collision keep higher-quality source (Nazario > IWSPA-AP > Kaggle)
4. Audit Kaggle phishing (500-sample Kappa check — if Kappa < 0.70, exclude entirely)
5. Compute derived features: display/From mismatch, reply-to mismatch, free-email detection, URL structural features, attachment features, text statistics, brand impersonation features
6. Apply typosquatting detection with Unicode normalization
7. Explicitly assign structured features for all augmented/template-generated samples (do not inherit blindly)
8. Apply stratified sampling to hit class targets with era/subtype distribution
9. Generate sampling manifest
10. Split 70/15/15 with temporal constraint where timestamps are available

---

## Summary of Key Decisions

| Decision | Reasoning |
|---|---|
| Cap spam at 6–10k despite 118k available | Class balance; more spam doesn't improve spam recall, it hurts phishing recall |
| Augment phishing to 8–12k | Organic phishing data is too scarce; augmentation is necessary, not optional |
| Explicitly assign structured features for augmented samples | Inherited features from source can be wrong for template-generated samples |
| Require Kaggle quality audit | Label noise in phishing directly degrades recall |
| Enforce era stratification | Legacy-heavy training produces models that fail on modern attacks |
| Enforce subtype coverage for phishing | A model that misses BEC or invoice fraud has failed operationally |
| Version the sampling manifest | Reproducibility and debugging; without it, dataset composition is unauditable |
| Exclude SMS data | Wrong modality; would introduce noise, not signal |
| Deduplicate across datasets before sampling | Same email in train+test inflates metrics |
