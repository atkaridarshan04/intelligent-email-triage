# Track A — Step-by-Step Execution Plan

## Overview

Track A is responsible for:
1. Building the **Spam class** (~20k samples, stratified by era and source)
2. Building the **Phishing class** (~20k samples, stratified by subtype, augmented to fill the organic gap)
3. Writing `shared/domains.txt`, `shared/ips.txt`, `shared/urls.txt` — the handoff that unblocks Track B's external lookups

All phases run in parallel with Track B from day 1. The shared file write (Phase 6) is the only output Track B depends on.

---

## Phase 1: Setup

**1.1 — Create folder structure**
```
data/
  raw/trec07p/             ← TREC 2007 corpus, never modified
  raw/spamassassin/        ← SpamAssassin tarballs + CSV files, never modified
  raw/phishing/            ← Nazario CSV, never modified
  interim/parsed_emails/   ← all parsed JSONL files (one per source)
  interim/deduplicated/    ← post-dedup JSONL per class
  processed/               ← final assembled class files ready for training
shared/                    ← handoff point: Track A writes domains.txt, ips.txt, urls.txt here
```

**1.2 — Install dependencies**
```
datasketch    ← MinHash LSH near-deduplication
pandas        ← CSV parsing (CEAS, SpamAssassin CSV, Nazario)
email         ← .eml parsing (stdlib)
```

---

## Phase 2: Download Raw Corpora

**Rule: raw files are never modified. All processing reads from them and writes to `data/interim/`.**

**2.1 — TREC 2007 Public Spam Corpus**
- Source: https://plg.uwaterloo.ca/~gvcormac/treccorpus07/
- Download `trec07p.tgz` (~255MB compressed)
- Extract to `data/raw/trec07p/`
- Structure after extraction:
  ```
  data/raw/trec07p/trec07p/
    full/index       ← label file: "spam ../data/inmail.N" or "ham ..."
    data/            ← individual .eml files named inmail.1, inmail.2, ...
  ```

**2.2 — SpamAssassin Corpus**
- Source: https://spamassassin.apache.org/old/publiccorpus/
- Download all 6 tarballs to `data/raw/spamassassin/`:
  ```
  20021010_spam.tar.bz2
  20030228_spam.tar.bz2
  20030228_spam_2.tar.bz2
  20050311_spam_2.tar.bz2
  20021010_hard_ham.tar.bz2
  20030228_hard_ham.tar.bz2
  ```
- Do not extract — `parse_spamassassin.py` reads directly from the archives.

**2.3 — CSV Corpora**
- CEAS 2008: download `CEAS_08.csv` → `data/raw/spamassassin/CEAS_08.csv`
- SpamAssassin CSV: download `SpamAssasin.csv` → `data/raw/spamassassin/SpamAssasin.csv`
- Nazario Phishing: download `Nazario.csv` → `data/raw/phishing/Nazario.csv`

---

## Phase 3: Parse All Corpora

Three parsers, one shared schema. All output to `data/interim/parsed_emails/`. Run all three independently — no dependencies between them.

**Shared schema every record must conform to:**
```json
{
  "source": "trec07 | spamassassin | ceas08 | nazario",
  "label": "spam | phishing",
  "subject": "...",
  "body_text": "... (capped at 5,000 chars)",
  "sender_display_name": "...",
  "headers": {
    "date": "...",
    "reply_to": "...",
    "received_spf": "...",
    "authentication_results": "...",
    "sending_ip": "..."
  },
  "urls": ["..."],
  "attachments": [{"count": 0, "mime_type": "", "filename": ""}],
  "spf_result": "pass | fail | softfail | neutral | none | temperror | permerror",
  "dkim_result": "pass | fail | none | policy | neutral | temperror | permerror",
  "dmarc_result": "pass | fail | bestguesspass | none",
  "url_count": 0,
  "attachment_count": 0,
  "reply_to_mismatch": false,
  "html_text_ratio": 0.0,
  "augmented": false,
  "domain_age_reliable": false
}
```

**Missing auth headers → always `"none"`, never `null` or `0`.**

**3.1 — Parse TREC 2007**

```bash
python src/datasets/parsers/parse_trec.py
```

Output: `data/interim/parsed_emails/trec07_spam.jsonl`

How it works:
- Reads `full/index`, keeps only lines starting with `"spam"` — ham is discarded
- Resolves each filename to `data/raw/trec07p/trec07p/data/inmail.N`
- Parses each `.eml` with Python's `email` stdlib
- Extracts body text from `text/plain` parts; falls back to HTML-stripped text if no plain part
- Extracts URLs via regex from all MIME parts
- Reads `Received-SPF` header for SPF result; reads `Authentication-Results` for DKIM/DMARC
- Extracts sending IP from first `Received` header via `[x.x.x.x]` pattern
- Computes reply-to mismatch: `From` domain ≠ `Reply-To` domain
- Sets `domain_age_reliable=False` — TREC 2007 is a pre-2010 corpus

Expected output: ~50,000 spam records

**3.2 — Parse SpamAssassin Tarballs**

```bash
python src/datasets/parsers/parse_spamassassin.py
```

Outputs:
- `data/interim/parsed_emails/spamassassin_spam.jsonl` — spam tarballs
- `data/interim/parsed_emails/hard_ham.jsonl` — hard ham (Track B handoff for Junk seed)

How it works:
- Opens each `.tar.bz2` directly with `tarfile`, iterates members
- Reuses `parse_email_from_bytes` from `parse_trec.py` — same parser, same schema
- Spam tarballs → `label="spam"`, `source="spamassassin"`
- Hard ham tarballs → `label="junk"`, `source="spamassassin_hard_ham"` (written to separate file for Track B)

Expected output: ~3,800 spam, ~500 hard ham

**3.3 — Parse CSV Corpora**

```bash
python src/datasets/parsers/parse_csvs.py
```

Outputs:
- `data/interim/parsed_emails/csv_spam.jsonl` — CEAS 2008 + SpamAssassin CSV
- `data/interim/parsed_emails/csv_phishing.jsonl` — Nazario

How it works:
- Reads each CSV with pandas, filters to `label=1` rows
- Maps `subject`, `body`, `sender` columns to shared schema
- CSV sources have no full headers — `spf_result`, `dkim_result`, `dmarc_result` all set to `"none"`
- `domain_age_reliable` set from date field: `True` only if year ≥ 2018 (none of these corpora qualify)
- Nazario: all rows used, `label="phishing"`, `source="nazario"`

Expected output: ~23,500 spam, ~1,565 phishing

---

## Phase 4: Cross-Dataset Deduplication

**Run after all three parsers complete.**

```bash
python src/datasets/enrichment/dedup.py
```

Outputs:
- `data/interim/deduplicated/spam_deduped.jsonl`
- `data/interim/deduplicated/phishing_deduped.jsonl`

**Dedup logic — two passes per class:**

1. **Exact dedup** — `sha256(subject + body_text[:500])`. Same hash → discard.
2. **Near-dedup** — MinHash LSH, 128 permutations, Jaccard threshold 0.85. Near-duplicate → discard.

**On collision:** Keep the higher-quality source. Priority order (lower index = higher quality):
```
nazario > spamassassin > ceas08 > trec07
```

Records are sorted by source priority before dedup so the best version is always encountered first and kept.

**Why dedup before assembly:** TREC, CEAS, and SpamAssassin all draw from overlapping bulk mail campaigns. The same spam email frequently appears in multiple corpora. Deduplicating before sampling prevents the same email from appearing in both train and test sets, which would inflate metrics.

Expected output after dedup:
```
spam_deduped.jsonl     : ~42,000–45,000 records
phishing_deduped.jsonl : ~1,400–1,500 records
```

---

## Phase 5: Assemble Spam Class

```bash
python src/datasets/builders/assemble_spam.py
```

Output: `data/processed/spam_class.jsonl` — 20,000 records

**Stratified downsampling from ~42k → 20k.**

Era targets per dataset plan:
| Era | Target | Cap |
|---|---|---|
| Legacy (pre-2010) | ≤ 6,000 | ≤ 30% |
| Mid (2010–2018) | 8,000 | ~40% |
| Recent (≥ 2018) | ≥ 6,000 | ≥ 30% |

Era is inferred from the `Date` header where parseable (regex for 4-digit year), falling back to source heuristics:
- `trec07` → legacy
- `ceas08` → legacy
- `spamassassin` → legacy

**Source cap:** No single source > 40% of the final 20k set.

**Sampling order:**
1. Sample up to the era target from each era bucket
2. If total < 20,000 (because mid/recent pools are empty), fill remainder from legacy
3. Apply source cap — shuffle and drop records from over-represented sources
4. If still under 20,000 after source cap, relax cap to fill

**Important:** All available spam corpora are legacy era (2002–2008). Mid and recent era targets will not be met with current sources. The fill logic relaxes the legacy cap and logs this as a known limitation. Do not fail — fill and document.

---

## Phase 6: Assemble Phishing Class

```bash
python src/datasets/builders/assemble_phishing.py
```

Output: `data/processed/phishing_class.jsonl` — 20,000 records

**The gap:** Organic phishing after dedup is ~1,400 samples. Target is 20,000. ~18,600 samples must come from augmentation.

**Two augmentation methods:**

**Method 1 — Text perturbation of organic samples (inherit source metadata)**
- Duplicate each Nazario record, apply light subject variation: add `Re:` / `Fwd:` prefix, append `- Action Required`, or flip case on `your`/`Your`
- Metadata (SPF, DKIM, domain age, etc.) inherited from the original record
- Cap at 2,000 perturbed samples

**Method 2 — Template generation per subtype (explicit metadata)**
- Generate from templates with slot-filled variation (brands, exec names, company names, amounts, URLs)
- Metadata assigned explicitly — never derived from template text:

| Feature | Value |
|---|---|
| `spf_result` | `"fail"`, `"softfail"`, or `"none"` (weighted toward fail) |
| `dkim_result` | `"fail"` or `"none"` |
| `dmarc_result` | `"fail"` or `"none"` |
| `sender_domain_age_days` | random int 1–30 |
| `first_time_domain` | `True` |
| `reply_to_mismatch` | `True` for ~60% of samples; always `True` for BEC |
| `augmented` | `True` |
| `domain_age_reliable` | `False` |

**Subtype targets:**
| Subtype | Template count |
|---|---|
| `credential_harvesting` | 4,000 |
| `redirect_landing_page` | 6,000 |
| `bec` | 4,000 (800 per sub-pattern × 5) |
| `malware_delivery` | 3,000 |
| `invoice_payment_fraud` | 3,000 |

**BEC sub-patterns — all 5 must be covered:**
- `wire_transfer` — exec impersonation + urgent wire request
- `gift_card` — exec impersonation + gift card purchase request
- `invoice_change` — vendor impersonation + updated payment account
- `bank_account_change` — vendor impersonation + new bank details
- `payroll_redirect` — HR impersonation + direct deposit change

Each sub-pattern needs ~800 samples with varied exec names, company names, amounts, banks, and urgency phrasing.

**BEC hallmark:** Always set `reply_to_mismatch=True` for BEC samples — the reply-to address pointing to a personal Gmail/Hotmail is the defining infrastructure signal.

**Phishing URL generation:**
- Use lookalike URL patterns: `secure-{brand}-login.{tld}`, `{brand}.account-verify.{tld}`, IP-based URLs, URL shorteners
- TLDs drawn from high-risk list: `.xyz`, `.top`, `.tk`, `.ml`, `.click`, `.online`, `.site`, `.info`

**Nazario subtype assignment:** All organic Nazario records assigned `subtype="credential_harvesting"` — Nazario is predominantly credential/account-takeover phishing. This is an approximation; individual records are not audited per-record.

**Final assembly:** Combine organic + perturbed + all template subtypes, shuffle, trim to exactly 20,000.

---

## Phase 7: Extract Shared Files (Track B Handoff)

**Run after Phase 4 (dedup) completes. Does not need to wait for Phase 5 or 6.**

```bash
python src/datasets/enrichment/extract_shared.py
```

Outputs:
- `shared/domains.txt` — unique sender domains, one per line, sorted
- `shared/ips.txt` — unique sending IPs, one per line, sorted
- `shared/urls.txt` — unique URLs, one per line, sorted

**Input:** `spam_deduped.jsonl` + `phishing_deduped.jsonl` — the full deduped pools, not just the 20k sampled records. Using the full pool gives Track B broader coverage for its lookups.

**Extraction logic:**
- Sender domain: regex `@([\w.\-]+)` on `sender_display_name` field
- Sending IP: from `headers.sending_ip`; fallback to regex scan of `headers.authentication_results`
- URLs: from `urls` field + regex scan of `body_text`

**This write unblocks Track B's WHOIS, Spamhaus, and PhishTank lookup phases.**

---

## Phase Summary

| Phase | Depends On | Can Start |
|---|---|---|
| 1 — Setup | Nothing | Day 1 |
| 2 — Download corpora | Nothing | Day 1 |
| 3.1 — Parse TREC | Phase 2 (TREC download) | After TREC downloaded |
| 3.2 — Parse SpamAssassin | Phase 2 (SA download) | After SA downloaded |
| 3.3 — Parse CSVs | Phase 2 (CSV downloads) | After CSVs downloaded |
| 4 — Deduplication | Phase 3 (all parsers) | After all 3 parsers done |
| 5 — Assemble spam | Phase 4 | After dedup done |
| 6 — Assemble phishing | Phase 4 | After dedup done (parallel with Phase 5) |
| 7 — Extract shared files | Phase 4 | After dedup done (parallel with 5 + 6) |

Phases 5, 6, and 7 are all independent of each other — run them in parallel after Phase 4.

---

## Scripts Reference

| Script | Phase | Input → Output |
|---|---|---|
| `src/datasets/parsers/parse_trec.py` | 3.1 | `data/raw/trec07p/` → `parsed_emails/trec07_spam.jsonl` |
| `src/datasets/parsers/parse_spamassassin.py` | 3.2 | `*.tar.bz2` → `parsed_emails/spamassassin_spam.jsonl` + `hard_ham.jsonl` |
| `src/datasets/parsers/parse_csvs.py` | 3.3 | `CEAS_08.csv`, `SpamAssasin.csv`, `Nazario.csv` → `csv_spam.jsonl` + `csv_phishing.jsonl` |
| `src/datasets/enrichment/dedup.py` | 4 | all parsed JSONL → `deduplicated/spam_deduped.jsonl` + `phishing_deduped.jsonl` |
| `src/datasets/builders/assemble_spam.py` | 5 | `spam_deduped.jsonl` → `processed/spam_class.jsonl` |
| `src/datasets/builders/assemble_phishing.py` | 6 | `phishing_deduped.jsonl` → `processed/phishing_class.jsonl` |
| `src/datasets/enrichment/extract_shared.py` | 7 | `spam_deduped.jsonl` + `phishing_deduped.jsonl` → `shared/domains.txt`, `ips.txt`, `urls.txt` |
