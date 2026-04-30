# Track B — Step-by-Step Execution Plan

## Overview

Track B is responsible for:
1. Building the **Junk class** (no public dataset has this natively)
2. Running **feature enrichment** for the whole dataset (WHOIS, Spamhaus, PhishTank lookups)

Everything in Phases 1–6 runs in parallel with Track A from day 1. Phase 7 (external lookups) is the only step that waits for Track A.

---

## Phase 1: Setup

**1.1 — Create folder structure**
```
data/
  raw/enron/               ← original downloaded Enron archive, never modified
  raw/spamassassin/        ← original SpamAssassin files, never modified
  interim/enron_parsed/    ← all ~500k Enron emails parsed to JSON (unfiltered)
  interim/junk_candidates/ ← filtered Junk candidates + gold set annotation files
  interim/synthetic_junk/  ← template-generated synthetic Junk emails
  processed/               ← final feature vectors ready for training (parquet files)
shared/                    ← handoff point: Track A writes domains.txt, ips.txt, urls.txt here
cache/whois/               ← WHOIS results cached per domain (query once, reuse forever)
cache/spamhaus/            ← Spamhaus ZEN blocklist results cached per IP
cache/phishtank/           ← PhishTank/SURBL URL hit results cached
```

**1.2 — Install dependencies**
```
python-whois       ← WHOIS lookups
datasketch         ← MinHash LSH deduplication
scikit-learn       ← Cohen's Kappa
pandas             ← data handling
email              ← parsing .eml/.mbox files (stdlib)
beautifulsoup4     ← HTML parsing for body text + URL extraction
dnspython          ← Spamhaus ZEN DNS lookups
```

**1.3 — Build TLD risk score table** (no external dependency — do this first)

Create `data/tld_risk_scores.json`:
```json
{
  "high_risk":   [".xyz", ".top", ".tk", ".ml", ".ga", ".click", ".gq", ".cf"],
  "medium_risk": [".info", ".biz", ".online", ".site", ".website"],
  "low_risk":    [".com", ".org", ".net", ".edu", ".gov", ".co.uk", ".de", ".fr"]
}
```
Score mapping: high=3, medium=2, low=1, unknown=2 (default to medium if TLD not in table).

---

## Phase 2: Enron Corpus — Download, Parse, Filter

**2.1 — Download**
- Source: https://www.cs.cmu.edu/~enron/
- File: `enron_mail_20150507.tar.gz` (~432MB)
- Extract to `data/raw/enron/`

**2.2 — Parse all emails**

For each file in the Enron maildir structure, parse using Python's `email` stdlib. Extract:
```
subject, body_text, sender_display_name,
from_address, to_address, date,
headers (full dict), urls (list),
attachments (list of {mime_type, filename})
```
Missing auth headers → set to `"none"` (never null or 0).

**2.3 — Filter for external non-business mail**

Keep an email only if ALL of these are true:
- `From` domain ≠ `@enron.com`
- Not a known Enron partner domain (build a small exclusion list: major energy companies, law firms)
- No phishing signals: no auth failures, no suspicious URLs, no credential-request language
- Content matches at least one of: vendor solicitation, event invite, mailing list, B2B outreach, promotional offer

Expected yield: ~2,000–5,000 emails from ~500k total.

**2.4 — Compute Enron behavioral history**

Before any split, group all Enron emails by sender across the full corpus:
```
sender_seen_before      = has this sender emailed this recipient before?
communication_frequency = count of prior emails from this sender to this recipient
first_time_domain       = is this the first email from this sender's domain to this recipient?
send_hour_deviation     = abs(email_hour - sender's median send hour)
```
Must be computed on the full corpus before train/val/test split — otherwise you'd be computing history using future emails.

Save to `data/interim/enron_behavioral_history.json`.

---

## Phase 3: Synthetic Junk Generation

**3.1 — Write templates for 5 categories**

Each category needs at least 3–5 base templates with slot lists:

| Category | Example subject |
|---|---|
| Consulting solicitations | "Quick question about {service} for {company}" |
| Webinar invites | "Join us: {topic} — {date}" |
| Reward/loyalty offers | "You've earned {points} points, redeem now" |
| SaaS trial promotions | "Start your free {duration} trial of {product}" |
| B2B vendor outreach | "We supply {product_category} to companies like yours" |

**3.2 — Generate samples**

Fill slots with varied values (sender names, company names, offer details, urgency phrases).
Target: ~8,000–12,000 synthetic Junk samples total.

**Validation check per generated sample — discard if it contains:**
- Credential requests ("enter your password", "verify your login")
- Financial fraud context (wire transfer, gift card, invoice payment)
- Executive impersonation
- Urgency + account suspension language ("your account will be suspended")
- Lookalike domains

**3.3 — Assign metadata explicitly for every synthetic sample**

Do not derive metadata from template text — assign it directly:

| Feature | Value |
|---|---|
| `spf_result` | `"pass"` |
| `dkim_result` | `"pass"` or `"none"` (50/50 — misconfiguration is common in bulk senders) |
| `dmarc_result` | `"none"` |
| `sender_domain_age_days` | random int 365–3650 |
| `tld_risk_score` | 1 (low risk) |
| `reply_to_mismatch` | `False` |
| `html_text_ratio` | random float 0.3–2.0 |
| `url_count` | random int 1–5 |
| `attachment_count` | 0 |
| `sender_seen_before` | `False` |
| `first_time_domain` | `True` |
| `communication_frequency` | 0 |
| `send_hour_deviation` | sample from realistic distribution (peak 9am–5pm) |
| `domain_age_reliable` | `True` (we assigned it) |
| `augmented` | `True` |

---

## Phase 4: Apply Junk Labeling Rules

Apply to all candidates (Enron filtered emails + synthetic generated emails).

**Label as Junk if at least 2 of:**
- Promotional / sales intent
- Bulk marketing style
- Irrelevant solicitation
- Low sender trust
- Misleading clickbait language
- Generic urgency

**Discard from Junk if it contains ANY of:**
- Credential harvesting request
- Payment change or wire transfer request
- Login / verification prompt
- Impersonation of a known brand or executive
- Malware attachment or lure
- Urgent account suspension language

Save all labeled candidates to `data/interim/junk_candidates/junk_labeled.jsonl`.

---

## Phase 5: Behavioral Feature Simulation + Noise Injection

Enron samples already have real behavioral features from Phase 2. This phase is for synthetic samples only.

**Base simulation:**
```
sender_seen_before:      False
first_time_domain:       False
communication_frequency: 0
```

**Noise injection (apply after base simulation):**
- Randomly select ~15% of Junk samples → set `first_time_domain=True`
- `send_hour_deviation`: sample from a realistic distribution, not a fixed value

Why: prevents the model from learning `first_time_domain=False` as a hard Junk rule. In production, new legitimate senders exist.

---

## Phase 6: Gold Set Validation

**6.1 — Random sample 500**

Randomly sample 500 emails from the full Junk candidate pool (organic + synthetic combined).
Save to `data/interim/gold_set_500.jsonl`.

**6.2 — Round 1 annotation**

You and your teammate independently label each of the 500 as:
`junk` / `spam` / `phishing` / `legitimate`

Do NOT look at the weak label when annotating. Save to separate files:
- `gold_set_labels_you.csv`
- `gold_set_labels_teammate.csv`

**6.3 — Compute Kappa**
```python
from sklearn.metrics import cohen_kappa_score
kappa = cohen_kappa_score(your_labels, teammate_labels)
print(kappa)
```

**6.4 — Decision**

| Result | Action |
|---|---|
| Kappa ≥ 0.75 | Proceed to Phase 7 |
| Kappa < 0.75 | Go to Round 2 (see below) |

**Round 2 (if needed):**
1. Extract all emails where you and your teammate disagreed
2. Sit together — discuss each disagreement, identify which rule caused it
3. Update the labeling rules to resolve the ambiguity
4. Re-annotate only the disagreed subset with updated rules
5. Recompute Kappa on the full 500
6. If still < 0.75 → repeat

**Do not proceed to training until Kappa ≥ 0.75.**

---

## Phase 7: External Lookups (Waits for Track A)

Starts only after Track A drops:
- `shared/domains.txt`
- `shared/ips.txt`
- `shared/urls.txt`

**7.1 — WHOIS lookups (domain age)**
```python
import whois
# For each domain in shared/domains.txt:
result = whois.whois(domain)
# Cache to cache/whois/{domain}.json
# Set domain_age_reliable=False for emails dated pre-2010
```

**7.2 — Spamhaus ZEN lookups (IP reputation)**
```python
import dns.resolver
# To check IP 1.2.3.4 → reverse to 4.3.2.1.zen.spamhaus.org
# DNS returns result → ip_listed=True
# DNS returns NXDOMAIN → ip_listed=False
# Cache to cache/spamhaus/{ip}.json
```

**7.3 — PhishTank / SURBL lookups (URL reputation)**
- Download PhishTank verified phishing URL list (CSV, updated daily)
- For each URL in `shared/urls.txt`: check if it appears in the list
- Cache as binary: `phishtank_hit=True/False`
- Save to `cache/phishtank/url_hits.json`

All results cached. Never re-query at training or inference time.

---

## Phase 8: Merge & Final Feature Vectors

**8.1 — Merge all Junk samples** (Enron filtered + synthetic) with their full feature vectors

**8.2 — Verify every sample has the complete feature vector**

```
Text:       subject, body_text, sender_display_name, url_token_text
Metadata:   spf_result, dkim_result, dmarc_result, url_count, attachment_count,
            sender_domain_age_days, tld_risk_score, reply_to_mismatch,
            html_text_ratio, sender_reputation_score
Behavioral: sender_seen_before, historical_sender_trust, communication_frequency,
            send_hour_deviation, first_time_domain, campaign_burst_score,
            lookalike_domain_detected
```

Drop any sample missing more than 2 metadata/behavioral features.

**8.3 — Generate sampling manifest**

For every sample:
```
source | era_bucket | subtype | label | augmented | domain_age_reliable | split
```
Era buckets: `legacy` < 2010, `mid` 2010–2018, `recent` ≥ 2018

**8.4 — Hand off for merge with Track A**

Your outputs:
- `data/processed/junk_features.parquet`
- `data/processed/junk_manifest.csv`

Track A outputs:
- `data/processed/spam_features.parquet`
- `data/processed/phishing_features.parquet`

Final merge → 70/15/15 stratified split with temporal constraint → `train.parquet`, `valid.parquet`, `test.parquet`

---

## Phase Summary

| Phase | Depends On | Start |
|---|---|---|
| 1 — Setup + TLD table | Nothing | Day 1 |
| 2 — Enron download + parse + filter | Nothing | Day 1 |
| 3 — Synthetic generation | Nothing | Day 1 |
| 4 — Apply labeling rules | Phase 2 + 3 | After 2 + 3 done |
| 5 — Behavioral simulation + noise | Phase 4 | After 4 done |
| 6 — Gold set validation (2 rounds) | Phase 4 | After 4 done — potentially blocking |
| 7 — External lookups | Track A shared files | After Track A drops files |
| 8 — Merge + manifest + split | Phase 6 + 7 | After both complete |
