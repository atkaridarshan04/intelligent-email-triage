# Dataset Construction: Parallel Work Split

## True Parallel Split

### Track A — Spam & Phishing Class Assembly

Works entirely on: TREC, CEAS, SpamAssassin spam, Nazario, IWSPA-AP, Kaggle

1. Download + parse those corpora
2. Run cross-dataset deduplication (hash + MinHash LSH across all phishing sources; also across spam sources)
3. Audit Kaggle (500-sample Kappa check — if Kappa < 0.70, exclude entirely)
4. Assemble spam class (6–10k, stratified by era/style):
   - Era cap: legacy (pre-2010) ≤ 30%, mid (2010–2018) ~40%, recent (≥ 2018) ≥ 30%
   - Style coverage: marketing, scam, bulk, newsletter
5. Assemble phishing class (8–12k, stratified by subtype, augment to fill gap):
   - Text perturbation of real samples → inherit source structured features
   - Template-generated samples → explicitly assign structured features: `reply_to_mismatch=True`, `sender_domain_age_days=1–30`, `free_email_sender=True` (where applicable)
   - BEC sub-patterns: minimum 200–300 samples per sub-pattern (wire transfer, gift card, invoice change, bank account change, payroll redirect)
6. Extract all unique sender domains and URLs → write to `shared/domains.txt`, `shared/urls.txt`

**Never touches:** Enron, Junk logic, external lookup APIs

---

### Track B — Feature Enrichment & Static Assets

Works entirely on: static brand lists, TLD tables, synthetic template generation

Steps 1–5 run from day 1 with zero dependency on Track A:

1. Build TLD risk score table (static, no external dependencies):
   - High risk (score 3): `.xyz`, `.top`, `.tk`, `.ml`, `.ga`, `.click`, `.gq`, `.cf`
   - Medium risk (score 2): `.info`, `.biz`, `.online`, `.site`, `.website`
   - Low risk (score 1): `.com`, `.org`, `.net`, `.edu`, `.gov`, `.co.uk`, `.de`, `.fr`

2. Build brand domain list for typosquatting detection (~500 known brand domains):
   - Microsoft, PayPal, Amazon, Google, Apple, Chase, Wells Fargo, etc.
   - Include Unicode normalization mappings (Cyrillic `а` → Latin `a`, etc.)

3. Build free-email provider list for sender detection:
   - Gmail, Yahoo, Outlook, Hotmail, AOL, ProtonMail, etc.

4. Generate synthetic spam templates across categories:
   - SaaS promotions, ecommerce campaigns, newsletters, affiliate offers, promotional bulk mail
   - Must NOT contain: credential requests, financial fraud context, executive impersonation, urgency + account suspension language
   - Assign structured features explicitly: `display_from_mismatch=False`, `reply_to_mismatch=False`, `free_email_sender=False`, `url_count=2–8`, `suspicious_tld_present=False`

5. Generate synthetic phishing templates across subtypes:
   - Credential harvesting, BEC sub-patterns, invoice fraud, payroll redirect, MFA reset
   - Polished language, realistic enterprise tone, subtle social engineering
   - Assign structured features explicitly: `reply_to_mismatch=True`, `sender_domain_age_days=1–30`, `free_email_sender=True` (where applicable), `typosquatting_detected=True` (for brand impersonation variants)

6. Validate synthetic samples against exclusion rules:
   - Spam synthetic: no credential requests, no impersonation, no financial fraud context
   - Phishing synthetic: must contain at least one high-weight phishing signal

**Step 7 (waits for Track A):** As soon as Track A drops `shared/domains.txt`, `shared/urls.txt` → compute derived features for all samples:
   - Typosquatting similarity: edit distance against brand domain list with Unicode normalization
   - TLD risk score: lookup against TLD table
   - URL entropy: Shannon entropy of URL domain strings
   - Shortened URL detection: pattern match against known shortener domains

---

## The Only Real Dependency

```
Track A writes shared/domains.txt, urls.txt
                        ↓
Track B computes typosquatting, TLD risk, URL entropy, shortener detection
                        ↓
Both tracks merge outputs → final feature vectors → manifest → 70/15/15 split
```

Everything before that arrow is fully parallel. The merge at the end is a short integration step, not a blocker on either track's core work.

---

## Shared Contract

| Item | Value |
|---|---|
| Email JSON fields | `subject`, `body_text`, `sender_display_name`, `headers` (dict), `urls` (list), `attachments` (list of `{count, mime_type, filename}`) |
| Missing structured features | `false` for boolean fields, `0` for numeric — never `null` |
| Era buckets | `legacy` < 2010, `mid` 2010–2018, `recent` ≥ 2018 |
| Labels | `"spam"`, `"phishing"` |
| Manifest schema | `source, era_bucket, subtype, label, augmented, split` |
| Exclude threshold | > 2 missing structured features → drop sample |
| Deduplication | Hash on `sha256(subject + body_text[:500])`; MinHash LSH Jaccard ~0.85 for near-dupes; on collision keep higher-quality source (Nazario > IWSPA-AP > Kaggle) |
| Synthetic cap | ≤ 25% of total samples across both classes |
