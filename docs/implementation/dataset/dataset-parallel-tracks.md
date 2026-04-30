# Dataset Construction: Parallel Work Split

## True Parallel Split

### Track A — Spam & Phishing Class Assembly
Works entirely on: TREC, CEAS, SpamAssassin spam, Nazario, IWSPA-AP, Kaggle

1. Download + parse those corpora
2. Run cross-dataset deduplication (hash + MinHash LSH across all phishing sources; also across spam sources)
3. Audit Kaggle (500-sample Kappa check — if Kappa < 0.70, exclude entirely)
4. Assemble spam class (~20k, stratified by era/style)
5. Assemble phishing class (~20k, stratified by subtype, augment to fill gap):
   - Text perturbation of real samples → inherit source metadata
   - Template-generated samples → explicitly assign metadata from label-specific distribution (`spf=fail`, `dkim=fail`, `domain_age=1–30 days`, `first_time_domain=True`)
   - BEC sub-patterns: ~2,000 samples minimum, covering all 5 sub-patterns (wire transfer, gift card, invoice change, bank account change, payroll redirect)
6. Extract all unique sender domains, IPs, URLs → write to `shared/domains.txt`, `shared/ips.txt`, `shared/urls.txt`

**Never touches:** Enron, Junk logic, external lookups

---

### Track B — Junk Class + Feature Enrichment
Works entirely on: Enron, synthetic templates, external lookup APIs

Steps 1–5 run from day 1 with zero dependency on Track A:

1. Download + parse Enron → filter external non-business mail → Junk candidates
   - Keep: `From` domain ≠ `@enron.com`, promotional/solicitation language, no phishing signals
   - Exclude: internal Enron mail, known partner domains, any auth failures or suspicious URLs
2. Generate synthetic Junk templates across 5 categories:
   - Consulting solicitations
   - Webinar invites
   - Reward point / loyalty offers
   - SaaS trial promotions
   - B2B vendor outreach
   - Each template must NOT contain: credential requests, financial fraud context, executive impersonation, urgency + account suspension language, lookalike domains
   - Assign metadata explicitly: `spf=pass`, `dkim=pass or none`, `domain_age=365–3650 days`, `first_time_domain=True`, `sender_seen_before=False`
3. Apply Junk labeling rules to all candidates (organic + synthetic)
4. Build TLD risk score table (static, no external dependencies):
   - High risk (score 3): `.xyz`, `.top`, `.tk`, `.ml`, `.ga`, `.click`, `.gq`, `.cf`
   - Medium risk (score 2): `.info`, `.biz`, `.online`, `.site`, `.website`
   - Low risk (score 1): `.com`, `.org`, `.net`, `.edu`, `.gov`, `.co.uk`, `.de`, `.fr`
5. Compute Enron behavioral history (sender frequency, first-contact, send-hour patterns) — group all emails by sender before splitting
6. Simulate behavioral features for non-Enron samples based on label; apply noise injection:
   - ~15% of spam/junk samples: set `first_time_domain=True`
   - ~10% of phishing samples: set `sender_seen_before=True`
   - `send_hour_deviation`: sample from realistic distribution, not fixed value
7. Run gold set validation — **plan for two rounds:**
   - Round 1: two annotators independently label 500 random samples → compute Kappa
   - If Kappa < 0.75: review disagreements, refine labeling rules, re-annotate disagreed subset
   - Round 2: re-measure Kappa on full set
   - Only proceed if Kappa ≥ 0.75 — treat as potentially blocking

**Step 8 (waits for Track A):** As soon as Track A drops `shared/domains.txt`, `shared/ips.txt`, `shared/urls.txt` → run WHOIS, Spamhaus ZEN, PhishTank/SURBL lookups and cache results:
   - WHOIS: set `domain_age_reliable=False` for all pre-2010 email domains
   - Spamhaus ZEN: DNS lookup against `zen.spamhaus.org` per sending IP
   - PhishTank/SURBL: binary hit/no-hit per URL, cached

---

## The Only Real Dependency

```
Track A writes shared/domains.txt, ips.txt, urls.txt
                        ↓
Track B runs external lookups (WHOIS, Spamhaus, PhishTank/SURBL)
                        ↓
Both tracks merge outputs → final feature vectors → manifest → 70/15/15 split
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
| Manifest schema | `source, era_bucket, subtype, label, augmented, domain_age_reliable, split` |
| Exclude threshold | > 2 missing metadata/behavioral features → drop sample |
| Deduplication | Hash on `sha256(subject + body_text[:500])`; MinHash LSH Jaccard ~0.85 for near-dupes; on collision keep higher-quality source |
