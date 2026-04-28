# Dataset Construction: Parallel Work Split

## True Parallel Split

### Track A — Spam & Phishing Class Assembly
Works entirely on: TREC, CEAS, SpamAssassin spam, Nazario, IWSPA-AP, Kaggle

1. Download + parse those corpora
2. Audit Kaggle (500-sample Kappa check)
3. Assemble spam class (~20k, stratified by era/style)
4. Assemble phishing class (~20k, stratified by subtype, augment to fill gap)
5. Extract all unique sender domains, IPs, URLs → write to `shared/domains.txt`, `shared/ips.txt`, `shared/urls.txt`

**Never touches:** Enron, Junk logic, external lookups

---

### Track B — Junk Class + Feature Enrichment
Works entirely on: Enron, synthetic templates, external lookup APIs

1. Download + parse Enron → filter external non-business mail → Junk candidates
2. Generate synthetic Junk templates (consulting, webinar, promo, B2B outreach)
3. Apply Junk labeling rules + gold set validation (Kappa > 0.75)
4. Compute Enron behavioral history (sender frequency, first-contact, send-hour)
5. Build TLD risk score table (static, no dependencies)
6. **As soon as Track A drops `shared/domains.txt`, `shared/ips.txt`, `shared/urls.txt`** → run WHOIS, Spamhaus ZEN, PhishTank/SURBL lookups and cache results

Steps 1–5 run from day 1 with zero dependency on Track A.

---

## The Only Real Dependency

```
Track A writes shared/domains.txt, ips.txt, urls.txt
         ↓
Track B runs external lookups (step 6)
         ↓
Both tracks merge outputs → final feature vectors → manifest → split
```

Everything before that arrow is fully parallel. The merge at the end is a short integration step, not a blocker on either track's core work.

---

## Shared Contract

| Item | Value |
|---|---|
| Email JSON fields | `subject`, `body_text`, `sender_display_name`, `headers` (dict), `urls` (list), `attachments` (list of `{count, mime_type, filename}`) |
| Missing auth headers | `"none"` — never `null` or `0` |
| Era buckets | `legacy` < 2010, `mid` 2010–2018, `recent` ≥ 2018 |
| Labels | `"spam"`, `"junk"`, `"phishing"` |
| Manifest schema | `source, era_bucket, subtype, label, augmented, split` |
| Exclude threshold | > 2 missing metadata/behavioral features → drop sample |
