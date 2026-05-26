# Dataset Audit Report — Intelligent Email Triage Dataset

## Executive Summary

A full exploratory data audit was performed on the processed dataset:

* **train:** 15,399 samples
* **validation:** 3,299 samples
* **test:** 3,302 samples
* **total:** 22,000 samples

The dataset is structurally consistent, but several **serious data quality and evaluation integrity issues** were identified.

Primary concerns:

* data leakage through overlapping email content
* synthetic augmentation leakage into validation/test
* severe train/validation/test distribution drift
* source provenance leakage
* weak / low-signal engineered fields
* task framing mismatch (binary phishing vs spam, not spam detection)

These issues should be corrected before model training.

---

# 1. Schema Integrity

## Findings

All splits share identical schema:

* 31 columns
* same field names
* same inferred data types

No schema mismatch detected.

### Result

✅ PASS

---

# 2. Duplicate Record Analysis

## Findings

### Exact duplicate rows

| Split      | Duplicate Rows |
| ---------- | -------------- |
| Train      | 0              |
| Validation | 0              |
| Test       | 0              |

### Duplicate IDs

| Split      | Duplicate IDs |
| ---------- | ------------- |
| Train      | 0             |
| Validation | 0             |
| Test       | 0             |

## Interpretation

No direct record duplication or ID reuse.

### Result

✅ PASS

---

# 3. Cross-Split Leakage Analysis

## Findings

### ID overlap

| Pair             | Overlap |
| ---------------- | ------- |
| Train–Validation | 0       |
| Train–Test       | 0       |
| Validation–Test  | 0       |

### Email body overlap (normalized text hash)

| Pair             | Overlap |
| ---------------- | ------- |
| Train–Validation | 10      |
| Train–Test       | 11      |
| Validation–Test  | 15      |

## Interpretation

Although IDs are unique, duplicate or near-identical email bodies exist across splits.

This introduces evaluation leakage because the model may encounter essentially identical samples during training and evaluation.

## Risk

Medium to High

## Fix

Deduplicate across splits using normalized email body hash:

```python
normalized = " ".join(body_text.lower().split())
hash = sha256(normalized)
```

Remove overlapping samples before re-splitting.

### Result

⚠️ FAIL

---

# 4. Augmentation Leakage

## Findings

| Split      | Augmented Samples |
| ---------- | ----------------- |
| Train      | 424               |
| Validation | 90                |
| Test       | 92                |

## Interpretation

Synthetic/augmented samples are present in evaluation sets.

Validation and test sets must represent untouched real-world data.

Including augmented samples contaminates evaluation and inflates performance estimates.

## Risk

High

## Fix

Remove augmented samples from validation/test:

```python
val = val[val["augmented"] == False]
test = test[test["augmented"] == False]
```

If needed, re-split from clean data.

### Result

❌ FAIL

---

# 5. Source Leakage

## Findings

### Train sources

* spamassassin_csv
* nigerian_fraud
* trec
* enron
* nazario
* spamassassin
* ceas
* phishing_email
* ling
* synthetic

### Validation sources

* phishing_email
* ceas
* synthetic

### Test sources

* phishing_email
* ceas
* enron
* synthetic

## Interpretation

Source distribution is severely inconsistent.

Many train-only corpora never appear in evaluation.

If `source` is included as a model feature, the model can trivially learn dataset provenance instead of phishing/spam behavior.

Even if excluded, source-specific linguistic patterns create distribution shift.

## Risk

Critical

## Fix

Drop:

```python
source
```

Then rebuild train/validation/test using random stratified splitting instead of source-based partitioning.

### Result

❌ FAIL

---

# 6. Distribution Drift

Major drift exists between train and evaluation splits.

---

## URL-based drift

| Metric            | Train | Validation | Test |
| ----------------- | ----- | ---------- | ---- |
| url_count mean    | 1.73  | 0.02       | 0.02 |
| domain_count mean | 0.80  | 0.02       | 0.02 |
| url_entropy mean  | 0.57  | 0.06       | 0.06 |

### Interpretation

Train emails contain far more URLs than validation/test.

Model may overfit URL-heavy phishing patterns.

---

## Subject drift

| Metric                | Train | Validation | Test |
| --------------------- | ----- | ---------- | ---- |
| subject_length mean   | 31.7  | 16.3       | 16.3 |
| subject_length median | 29    | 0          | 0    |

### Interpretation

Over half of evaluation emails have empty subjects.

Train data does not reflect this.

---

## Body length drift

| Metric             | Train | Validation | Test |
| ------------------ | ----- | ---------- | ---- |
| body_length mean   | 2195  | 621        | 750  |
| body_length median | 954   | 294        | 322  |

### Interpretation

Train emails are substantially longer.

---

## Style drift

| Metric              | Train | Validation | Test  |
| ------------------- | ----- | ---------- | ----- |
| uppercase_ratio     | 0.061 | 0.026      | 0.021 |
| punctuation_density | 0.065 | 0.027      | 0.028 |

### Interpretation

Writing style differs strongly across splits.

## Risk

Critical

## Fix

Rebuild dataset with stratified random splitting after deduplication and augmentation cleanup.

### Result

❌ FAIL

---

# 7. Null / Empty Value Audit

## Subject

| Split      | Empty Subjects |
| ---------- | -------------- |
| Train      | 699            |
| Validation | 1710           |
| Test       | 1710           |

Train empty rate:

~4.5%

Validation/test empty rate:

~52%

### Interpretation

Massive inconsistency.

---

## Attachment Type

| Split      | Empty Values |
| ---------- | ------------ |
| Train      | 15382        |
| Validation | 3299         |
| Test       | 3302         |

Only 17 train samples have non-empty attachment type.

Validation/test contain none.

### Interpretation

Feature has negligible utility.

---

## Era Bucket

Empty:

* Train: 11,379
* Validation: 0
* Test: 415

### Interpretation

Inconsistent semantics.

---

## Subtype

Empty:

* Train: 14,975
* Validation: 3,209
* Test: 3,210

Only a small subset populated.

Strong correlation with synthetic samples suspected.

---

# Fix

Drop:

```python
attachment_type
era_bucket
subtype
```

### Result

⚠️ FAIL

---

# 8. Feature Consistency Checks

## Findings

Checks passed:

* body_length matches actual body text length
* subject_length matches actual subject length
* digit_ratio within [0,1]
* uppercase_ratio within [0,1]
* link_density within [0,1]

## Interpretation

Engineered numeric features appear internally consistent.

### Result

✅ PASS

---

# 9. Task Definition Issue

## Findings

Labels:

```text
phishing
spam
```

No ham / legitimate class exists.

## Interpretation

Current task is:

**binary phishing vs spam classification**

NOT:

* spam detection
* phishing detection
* malicious email detection vs legitimate email

This changes project framing entirely.

## Risk

Conceptual / project design risk

## Fix

Clarify objective.

If legitimate email classification is required, add ham data.

### Result

⚠️ NEEDS DECISION

---

# Recommended Feature Drops

Remove before modeling:

```python
DROP_COLUMNS = [
    "id",
    "split",
    "source",
    "augmented",
    "subtype",
    "attachment_type",
    "era_bucket",
]
```

Potentially review:

```python
subject
body_text
```

depending on feature-only vs NLP model approach.

---

# Recommended Dataset Repair Pipeline

## Step 1 — Remove augmented evaluation data

```python
val = val[val["augmented"] == False]
test = test[test["augmented"] == False]
```

---

## Step 2 — Remove overlapping text

Deduplicate by normalized email body hash.

---

## Step 3 — Merge clean samples

Combine:

```python
train + val + test
```

after removing contaminated samples.

---

## Step 4 — Drop leakage columns

Remove identified unsafe fields.

---

## Step 5 — Rebuild splits

Perform stratified random split:

* train
* validation
* test

Preserve label distribution.

---

## Step 6 — Recompute engineered features if necessary

Ensure derived fields reflect clean split.

---

# Final Assessment

| Category                  | Status       |
| ------------------------- | ------------ |
| Schema integrity          | PASS         |
| Duplicate rows            | PASS         |
| Duplicate IDs             | PASS         |
| Text leakage              | FAIL         |
| Augmentation leakage      | FAIL         |
| Source leakage            | FAIL         |
| Distribution stability    | FAIL         |
| Numeric feature integrity | PASS         |
| Feature usefulness        | MIXED        |
| Task definition clarity   | NEEDS REVIEW |

---

# Overall Verdict

**Dataset is not ready for reliable model training in current form.**

Primary blockers:

1. augmentation leakage
2. source leakage
3. split distribution drift
4. overlapping content leakage

After repair, the dataset should be re-audited before training.
