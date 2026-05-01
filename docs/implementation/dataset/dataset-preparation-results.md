# Dataset Preparation — Results & Execution Record

Covers all steps from raw class files (Track A/B outputs) to final model-ready train/val/test splits.

---

## Inputs

| File | Records | Description |
|---|---|---|
| `data/processed/classes/spam_class.jsonl` | 20,000 | Spam class — Track A output |
| `data/processed/classes/phishing_class.jsonl` | 20,000 | Phishing class — Track A output |
| `data/processed/classes/junk_features.jsonl` | 17,639 | Junk class — Track B output |

---

## Final Outputs

| File | Records | Description |
|---|---|---|
| `data/processed/splits/train_augmented.jsonl` | 46,252 | Training set with phishing augmentation |
| `data/processed/splits/val.jsonl` | 8,645 | Validation set — clean, unaugmented |
| `data/processed/splits/test.jsonl` | 8,647 | Test set — clean, unaugmented, held out |

---

## Schema Decision

### Problem
The three class files had different schemas. True intersection across all three was only 11 fields. Junk had behavioral features (sender history, TLD score, etc.) that spam and phishing lacked entirely.

### Options Considered

| Option | Decision |
|---|---|
| Intersection only (11 fields) | Discards real signals unnecessarily |
| Union with nulls | Model learns feature availability as a class proxy — leakage |
| Synthesize missing behavioral features | `communication_frequency`, `send_hour_deviation` can't be assigned without fabrication or leakage |
| Intersection + 4 computable fields | ✅ Chosen |

### Chosen Schema (15 fields)

**Text (4):** `subject`, `body_text`, `sender_display_name`, `url_token_text`

**Metadata (8):** `spf_result`, `dkim_result`, `dmarc_result`, `url_count`, `attachment_count`, `reply_to_mismatch`, `html_text_ratio`, `tld_risk_score`

**Behavioral (2, merged into metadata encoder):** `sender_seen_before`, `first_time_domain`

**Target:** `label`

**Dropped behavioral features:** `communication_frequency`, `send_hour_deviation` — only exist for junk, assigning constants to spam/phishing would create a perfect class separator (leakage). Deferred to v2 with real inference-time data.

**Behavioral encoder:** Collapsed into the metadata MLP for v1. Only 2 boolean behavioral features — a dedicated encoder adds architectural overhead with no benefit. Split back out in v2 when more behavioral features are available.

`source` is carried as a passthrough field for augmentation targeting and must be dropped before model input.

---

## Phase 1 — Compute Missing Fields

**Script:** `src/datasets/builders/compute_missing_fields.py`

**Inputs:** `spam_class.jsonl`, `phishing_class.jsonl`
**Outputs:** `data/processed/enriched/spam_class_enriched.jsonl`, `phishing_class_enriched.jsonl`

Four fields added to spam and phishing:

| Field | Spam | Phishing |
|---|---|---|
| `url_token_text` | Extracted from `urls` list (netloc + path segments, space-joined) | Same |
| `tld_risk_score` | Computed via `tld_lookup.get_tld_score()` from sender domain in `sender_display_name` | Same |
| `sender_seen_before` | `False` (accurate — bulk/phishing senders have no prior history) | `False` |
| `first_time_domain` | `True` (accurate — spam always from unseen domains) | Nulls filled with `True`; organic Nazario records may have had null |

**Why these 4 are safe:**
- `url_token_text` and `tld_risk_score` are computed from existing fields — no fabrication.
- `sender_seen_before=False` for spam/phishing is factually accurate and not a perfect class separator — 29% of junk also has `sender_seen_before=False`.
- `first_time_domain=True` for spam is factually accurate. Phishing also has `first_time_domain=True` for most records, so it doesn't cleanly separate spam from phishing.

**Verification:** All 15 fields present, zero nulls across 500-sample check of all three files.

---

## Phase 2 — Merge

**Script:** `src/datasets/builders/merge_dataset.py`

**Inputs:** `spam_class_enriched.jsonl`, `phishing_class_enriched.jsonl`, `junk_features.jsonl`
**Output:** `data/processed/splits/dataset.jsonl` — 57,639 records, shuffled (seed=42)

Keeps only the 15 schema fields + `source` passthrough. Records shuffled before write.

**Counts:**
```
spam     : 20,000
phishing : 20,000
junk     : 17,639
total    : 57,639
```

---

## Phase 3 — Stratified Split

**Script:** `src/datasets/builders/split_dataset.py`

**Input:** `dataset.jsonl`
**Outputs:** `train.jsonl`, `val.jsonl`, `test.jsonl`

Stratified 70/15/15 split per class (seed=42). Class proportions maintained across all splits.

| Split | Total | Spam | Phishing | Junk |
|---|---|---|---|---|
| train | 40,347 | 14,000 | 14,000 | 12,347 |
| val | 8,645 | 3,000 | 3,000 | 2,645 |
| test | 8,647 | 3,000 | 3,000 | 2,647 |

Val and test are never touched after this point.

---

## Phase 4 — Training Set Augmentation

**Script:** `src/datasets/builders/augment_train.py`

**Input:** `train.jsonl`
**Output:** `data/processed/splits/train_augmented.jsonl`

**Why:** 85.6% of phishing class is template-generated (`source=augmented_template`). Without augmentation, the model risks learning template structure rather than phishing intent signals.

**What is augmented:** Only `source=augmented_template` phishing records in the training set (~11,984 samples). Spam and junk are not augmented.

**Augmentation strategy:** 50% of template samples get one augmented copy added (not replacing the original):
- Word dropout — randomly drop 10–15% of words from `body_text`
- Token shuffle — shuffle words within a randomly selected sentence
- Subject prefix — prepend a random noise prefix (`Re:`, `Fwd:`, `[Action Required]`, etc.) with 40% probability, applied on top of either augmentation

Each sample gets one augmentation type chosen at random. Augmented copies are added alongside originals.

**Result:**

| Split | Total | Spam | Phishing | Junk |
|---|---|---|---|---|
| train_augmented | 46,252 | 14,000 | 19,905 | 12,347 |
| val | 8,645 | 3,000 | 3,000 | 2,645 |
| test | 8,647 | 3,000 | 3,000 | 2,647 |

Phishing is slightly heavier in train due to augmented copies — intentional, aligns with the higher-penalty loss weighting for phishing false negatives.

---

## Known Limitations

| Limitation | Impact | Fix in v2 |
|---|---|---|
| `spf/dkim/dmarc` all `none` for spam and junk | Auth signals only informative for phishing in training | Add modern spam/junk sources with real auth headers |
| All spam is legacy era (2002–2008) | Model may not generalize to modern spam patterns | Add SpamAssassin 2019+, recent community corpora |
| 85.6% of phishing is template-generated | Model may learn template artifacts despite augmentation | Increase organic phishing proportion (IWSPA-AP, Kaggle after audit) |
| Behavioral encoder collapsed into metadata MLP | Behavioral signals not independently weighted | Restore dedicated behavioral encoder in v2 with full feature set |
| `source` field must be dropped at model input | Dataloader responsibility — not enforced in data files | Strip at dataset load time in training code |

---

## Scripts Reference

| Script | Input → Output |
|---|---|
| `src/datasets/builders/compute_missing_fields.py` | `classes/*.jsonl` → `enriched/*_enriched.jsonl` |
| `src/datasets/builders/merge_dataset.py` | `enriched/` + `classes/junk_features.jsonl` → `splits/dataset.jsonl` |
| `src/datasets/builders/split_dataset.py` | `splits/dataset.jsonl` → `splits/train.jsonl`, `val.jsonl`, `test.jsonl` |
| `src/datasets/builders/augment_train.py` | `splits/train.jsonl` → `splits/train_augmented.jsonl` |
