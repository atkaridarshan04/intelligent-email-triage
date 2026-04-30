# Track B — Results & Execution Record

Complete record of Track B execution: what was built, commands run, outputs produced, decisions made, and why.

---

## Final Outputs

| File | Records | Description |
|---|---|---|
| `data/processed/junk_features.parquet` | 17,639 | Unified Junk feature vectors, ready for training |
| `data/processed/junk_manifest.csv` | 17,639 | Per-sample metadata (source, era, subtype, augmented) |

### Dataset Composition
| Source | Count | Era |
|---|---|---|
| Enron organic | 7,639 | legacy (pre-2010) |
| Synthetic | 10,000 | recent |
| **Total** | **17,639** | |

---

## Phase 1 — Setup

**Commands:**
```bash
python -m venv venv
pip install -r requirements.txt
```

**Outputs:**
- `venv/` — isolated Python environment
- `requirements.txt` — pinned dependencies
- `data/tld_risk_scores.json` — TLD risk tier table (high/medium/low, scores 3/2/1)
- `src/utils/tld_lookup.py` — `get_tld_score(domain) → int`, unknown TLDs default to 2

---

## Phase 2.1 — Enron Download

**Source:** Kaggle CSV export of CMU Enron maildir archive
**Output:** `data/raw/enron/emails.csv` — 517,401 rows, 1.4GB
**Rule:** Raw file never modified. All processing reads from it and writes to `interim/`.

---

## Phase 2.2 — Parse All Emails

**Command:**
```bash
python src/datasets/parse_enron.py
```

**Output:** `data/interim/enron_parsed/enron_parsed.jsonl` — 517,401 records, 180MB

**Validation:**
```
Total records : 517,401
Missing keys  : 0
Null auth vals: 0
SPF/DKIM/DMARC: all "none" (expected — Enron emails are 2000–2002, predating these protocols)
Has URLs      : 67,148
Empty body    : 0
```

**Decision — resume support:** Session interrupted at row 55,527. Added resume logic: script counts existing lines in output on startup, skips that many CSV rows, opens output in append mode. Re-ran and completed.

**Sample record:**
```json
{
  "file": "allen-p/all_documents/2.",
  "subject": "December Newsletter - Factory Incentives are at a year-long high!",
  "from_address": "bounce-news-932653@lists.autoweb.com",
  "spf_result": "none", "dkim_result": "none", "dmarc_result": "none",
  "urls": ["http://www.autoweb.com/nl12.htm"],
  "html_text_ratio": 0.0, "reply_to_mismatch": false
}
```

---

## Phase 2.3 — Filter for Junk Candidates

**Command:**
```bash
python src/datasets/filter_enron.py
```

**Output:** `data/interim/junk_candidates/enron_junk_candidates.jsonl` — 13,729 records

**Filter logic (3 gates, all must pass):**
1. Domain gate — drops `@enron.com`, known partner domains (energy cos, law firms, trading counterparties), personal freemail (aol/hotmail/yahoo), academic (.edu)
2. Phishing disqualifier — drops credential language, financial fraud, account suspension, malware lures, auth failures, IP-based URLs
3. Junk signal gate — requires strong signal (explicit unsubscribe/opt-out, vendor/B2B, webinar, loyalty offer) OR ≥2 weak signals (promo language, newsletter markers, bulk CTAs)

**Iteration — first run yielded 22,893:**
- Root cause: JUNK_RE too broad (`click here`, `newsletter`, `dear member` matching news digests)
- Initial over-correction: excluded news/media domains (nytimes, motleyfool, earnings.com)
- **Corrected decision:** Newsletters ARE valid Junk per spec — "unsolicited bulk from a legitimate sender." Only personal freemail and academic domains excluded. Tightened signal requirement instead.
- Final yield: 13,729

---

## Phase 2.4 — Compute Enron Behavioral History

**Command:**
```bash
python src/datasets/compute_behavioral_history.py
```

**Output:** `data/interim/enron_behavioral_history.json` — 7,639 entries keyed by `file` path

**How it works:** Two-pass algorithm over full 517k corpus sorted chronologically. Running tallies of `pair_count[(sender, recipient)]`, `domain_pair_count[(domain, recipient)]`, `sender_hours[sender]`. For each target email, features recorded from tally state *before* that email is added — strict no-leakage guarantee.

**Results:**
```
sender_seen_before=True : 5,411 / 7,639  (71%)
first_time_domain=True  : 1,368 / 7,639  (18%)
send_hour_deviation     : mean=3.28h, median=1h
communication_frequency : 2,228 first-contact, long tail to 20+
```

High `sender_seen_before` rate (71%) expected — most Junk candidates are recurring newsletters.

---

## Phase 3 — Synthetic Junk Generation

**Command:**
```bash
python src/datasets/generate_synthetic_junk.py
```

**Output:** `data/interim/synthetic_junk/synthetic_junk.jsonl` — 10,000 records

**5 categories, 2,000 each:**
| Category | Example subject |
|---|---|
| `consulting_solicitation` | "Quick question about process optimization for BlueSky Inc" |
| `webinar_invite` | "Join us: AI in enterprise security — Tuesday, May 14 at 2pm ET" |
| `loyalty_reward` | "You've earned 1,000 loyalty points — redeem now" |
| `saas_trial` | "Start your free 30-day trial of ProjectFlow" |
| `vendor_b2b` | "We supply office supplies to companies like yours" |

**Validation:** 0 discarded — all templates clean (verified by phishing check regex across 1,000 samples per category before generation).

**Metadata explicitly assigned per spec** — never derived from text:
`spf=pass`, `dkim=pass/none (50/50)`, `dmarc=none`, `tld_risk_score=1`, `sender_domain_age_days=365–3650`, `augmented=True`, `label="junk"`

**Why synthetic:** Enron is 2000–2002 era. Modern Junk (SaaS trials, webinar invites, B2B outreach) looks different. Synthetic fills the era gap.

**Phase 4 note:** Synthetic samples labeled at generation time (explicit `label="junk"` + inline phishing check). Phase 4 labeling rules ran on Enron candidates only — running them on synthetic would be redundant and could wrongly discard valid samples.

---

## Phase 4 — Apply Junk Labeling Rules (Enron only)

**Command:**
```bash
python src/datasets/label_junk.py
```

**Output:** `data/interim/junk_candidates/junk_labeled.jsonl` — 7,639 records

**Logic:** Two-stage check per email:
1. Disqualifiers (any one → discard): credential requests, financial fraud, executive impersonation, malware lures, account suspension
2. Positive signals (≥2 required): mailing_list_marker, newsletter_digest, promotional_offer, event_invite, vendor_b2b_outreach, loyalty_reward, bulk_marketing_style, bulk_cta

Each kept record gets `label="junk"`, `junk_score` (2–6), `matched_signals` (list of which rules fired).

**Results:**
```
Total candidates : 13,729
Labeled junk     : 7,639  (55.6%)
Discarded (disqualifier) : 97
Discarded (low score)    : 5,993
```

**Signal distribution:**
```
mailing_list_marker  : 6,603
promotional_offer    : 5,131
newsletter_digest    : 3,411
bulk_cta             : 1,087
vendor_b2b_outreach  :   920
bulk_marketing_style :   675
event_invite         :   551
loyalty_reward       :   178
```

---

## Phase 5 — Noise Injection

**Command:**
```bash
python src/datasets/inject_noise.py
```

**Output:** `data/interim/synthetic_junk/synthetic_junk_noised.jsonl` — 10,000 records

**What changed:** 15% of synthetic samples (1,500) had `first_time_domain` flipped from `True` to `False`.

**Why:** All synthetic samples were generated with `first_time_domain=True`. Without noise, model learns this as a hard Junk rule. In production, many legitimate first-contact emails exist. 15% noise forces the model to treat it as a signal, not a rule.

**Result:** `first_time_domain=True`: 8,500 / `first_time_domain=False`: 1,500 (15.0%) ✅

---

## Phase 6 — Gold Set Validation

**Command:**
```bash
python src/datasets/sample_gold_set.py
```

**Output:**
- `data/interim/gold_set_500.jsonl` — 500 sampled records (weak label stripped)
- `data/interim/gold_set_template.csv` — blank annotation template

**Sampling:** Stratified proportional to pool sizes — 217 Enron (43.4%) + 283 synthetic (56.6%) = 500. Pool shuffled so annotators don't see source pattern.

**Annotation:** Both annotators labeled independently as `junk` / `spam` / `phishing` / `legitimate`.

**Kappa script:** `src/datasets/compute_kappa.py` — loads both CSVs, computes Cohen's Kappa, prints full disagreement list if < 0.75.

---

## Phase 7 — External Lookups

### 7.1 WHOIS (domain age)
**Status: Failed — environment issue**

`python-whois` library hangs on bulk lookups due to inconsistent timeout behavior across WHOIS servers. Port 43 (raw TCP) is accessible but the library doesn't respect timeouts reliably on this machine.

**Decision:** `sender_domain_age_days = null` for all Enron records. `domain_age_reliable = False` in manifest. Feature will be available at inference time on real emails. Revisit with a better WHOIS tool in v2.

### 7.2 Spamhaus ZEN (IP reputation)
**Command:**
```bash
# Must use venv — system Python lacks dnspython
venv/bin/python src/datasets/spamhaus_lookup.py
```

**Issue:** First run used system Python (no `dnspython`) → 8,055 SERVFAIL errors. Re-ran with venv after clearing errored cache files.

**Final cache:** 12,128 IPs total
```
Listed (bad IPs) : 7,229  (59.6%)
Clean            :  4,895
Errors           :      4
```

**Note:** `ip_listed = None` for all records in final parquet — Enron CSV format strips Received headers (no real IPs), synthetic has no real IPs. Feature will be populated at inference time on real emails.

### 7.3 OpenPhish (URL reputation)
**Command:**
```bash
python src/datasets/phishtank_lookup.py
```

**Note:** PhishTank registration disabled. Switched to OpenPhish (no registration, plain text feed, updated every 12h).

**Result:**
```
URLs checked  : 43,782
Phishing hits : 0  (0.0%)
```

0 hits expected — URLs in training data are years old, no longer in active phishing feed. Feature will be useful at inference time on fresh emails.

---

## Phase 8 — Merge & Feature Vectors

**Command:**
```bash
venv/bin/pip install pyarrow==19.0.1   # missing dependency, added to requirements.txt
venv/bin/python src/datasets/merge_junk.py
```

**Outputs:**
- `data/processed/junk_features.parquet` — 17,639 × 21 feature matrix
- `data/processed/junk_manifest.csv` — source/era/subtype/augmented per sample

**Feature coverage:**
```
sender_domain_age_days : 10,000 present (synthetic only), 7,639 null (Enron — WHOIS failed)
ip_listed              : 0 present, 17,639 null (no real IPs in either source)
phishtank_hit          : 17,639 present (all False — old URLs not in active feed)
sender_seen_before     : 17,639 present
tld_risk_score         : 17,639 present
```

**Era distribution:**
```
recent : 10,000  (synthetic)
legacy : 7,639   (Enron, 2000–2002)
```

**Schema (21 columns):**
```
Text (4):       subject, body_text, sender_display_name, url_token_text
Metadata (10):  spf_result, dkim_result, dmarc_result, url_count, attachment_count,
                sender_domain_age_days, tld_risk_score, reply_to_mismatch,
                html_text_ratio, ip_listed, phishtank_hit
Behavioral (4): sender_seen_before, communication_frequency, send_hour_deviation,
                first_time_domain
IDs (2):        file, label
```

**Deferred features** (require live computation at inference, not dataset construction):
- `sender_reputation_score` — aggregate score, computed from multiple signals
- `historical_sender_trust` — derived from sender_seen_before + communication_frequency
- `campaign_burst_score` — requires volume analysis across emails
- `lookalike_domain_detected` — requires edit distance against brand domain list

---

## Known Limitations & v2 Improvements

| Limitation | Impact | Fix in v2 |
|---|---|---|
| `domain_age_days` null for all Enron records | Missing feature for 7,639 samples | Use `whois` CLI tool or alternative library with proper timeout |
| `ip_listed` null for all records | Feature unavailable in training | Enron CSV strips IPs; use raw maildir format if available |
| `phishtank_hit` all False | Feature not useful in training | Expected — old URLs. Useful at inference only |
| Gold set annotated by AI agents | Kappa validity uncertain | Human annotation in v2 |
| Enron era only legacy (2000–2002) | No mid-era organic Junk | Add SpamAssassin hard_ham corpus for mid-era coverage |

---

## Scripts Reference

| Script | Phase | Input → Output |
|---|---|---|
| `src/datasets/parse_enron.py` | 2.2 | `data/raw/enron/emails.csv` → `enron_parsed.jsonl` |
| `src/datasets/filter_enron.py` | 2.3 | `enron_parsed.jsonl` → `enron_junk_candidates.jsonl` |
| `src/datasets/compute_behavioral_history.py` | 2.4 | `enron_parsed.jsonl` → `enron_behavioral_history.json` |
| `src/datasets/generate_synthetic_junk.py` | 3 | — → `synthetic_junk.jsonl` |
| `src/datasets/label_junk.py` | 4 | `enron_junk_candidates.jsonl` → `junk_labeled.jsonl` |
| `src/datasets/inject_noise.py` | 5 | `synthetic_junk.jsonl` → `synthetic_junk_noised.jsonl` |
| `src/datasets/sample_gold_set.py` | 6.1 | both pools → `gold_set_500.jsonl` + template CSV |
| `src/datasets/compute_kappa.py` | 6.3 | two annotation CSVs → Kappa score |
| `src/datasets/whois_lookup.py` | 7.1 | `shared/domains.txt` → `cache/whois/*.json` |
| `src/datasets/spamhaus_lookup.py` | 7.2 | `shared/ips.txt` → `cache/spamhaus/*.json` |
| `src/datasets/phishtank_lookup.py` | 7.3 | `shared/urls.txt` → `cache/phishtank/url_hits.json` |
| `src/datasets/merge_junk.py` | 8 | all interim → `junk_features.parquet` + `junk_manifest.csv` |
