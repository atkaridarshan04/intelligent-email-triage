# Dataset Construction Plan

## The Core Problem

The datasets.md already identifies the right sources. What it doesn't fully resolve is **how much to use from each, in what form, and why** — especially given three constraints that pull against each other:

1. Phishing samples are rare in the wild (~5–10% of raw data), but the model needs >98% phishing recall
2. The Junk class doesn't exist natively in any public dataset — it must be constructed
3. Most public datasets are old (pre-2015), but the model needs to generalize to modern attack patterns

Every decision below is driven by those three constraints.

---

## Dataset Selection: What to Use and Why

### Spam Class

**Use: TREC 2007 (~75k) + SpamAssassin spam partition (~3k) + CEAS 2008 (~40k)**

TREC 2007 is the backbone. It's the largest, best-structured, and has chronological ordering — which is essential for temporal evaluation (train on early emails, test on later ones). CEAS 2008 adds volume and stylistic diversity. SpamAssassin spam is small but high-quality and well-curated.

Ling-Spam (~2,900 total, ~480 spam) is too small and too domain-specific (linguistics mailing list) to contribute meaningfully to spam diversity. **Exclude from spam training; use only for cross-dataset generalization testing.**

UCI SMS Spam: SMS context is fundamentally different — no headers, no HTML, no URLs, no authentication signals. The transformer will learn SMS-specific patterns that don't transfer. **Exclude from training entirely.** It's not useful here.

**Raw spam available: ~118k samples. Target: ~20k after stratified downsampling.**

Why only 20k from 118k? Because spam is already the majority class. Using all 118k would require proportionally inflating phishing to ~120k (which doesn't exist) or training on a severely imbalanced set. 20k is enough to learn spam patterns thoroughly while keeping the training set balanced.

Downsampling strategy: stratify by era (legacy/mid/recent) and spam style (marketing, scam, bulk, newsletter). Don't just take the first 20k — that would over-represent the oldest samples.

---

### Phishing Class

**Use: Nazario (~2k) + IWSPA-AP + Kaggle Phishing (after quality filtering) + PhishTank URL-enriched samples**

This is the hardest class to populate. The total organic phishing data from public sources is roughly 5,000–8,000 samples after deduplication and quality filtering. That's not enough for a 20k target.

**Nazario** is the most cited and most reliable. Use all of it.

**IWSPA-AP** is specifically designed for ML phishing detection and includes spear phishing — a subtype that's underrepresented elsewhere. Use all of it.

**Kaggle Phishing**: Community datasets have variable label quality. The plan is to use it, but with a mandatory quality gate: cross-check a random 500-sample audit against Nazario/IWSPA-AP label definitions. If inter-rater agreement (Cohen's Kappa) < 0.70, exclude it. If it passes, use the verified portion.

**PhishTank**: This is URL data, not full emails. It can't directly produce training samples, but it can enrich existing phishing samples with confirmed-malicious URL labels, and it can be used to construct synthetic phishing samples with known-bad URLs embedded in realistic email templates.

**The gap problem**: Even with all organic sources, you'll have ~5–8k phishing samples. The 20k target requires augmentation.

**Augmentation strategy for phishing:**

1. **SMOTE on metadata/behavioral features** — generate synthetic feature vectors in the neighborhood of real phishing samples. This works well for the structured MLP inputs (SPF/DKIM results, domain age, URL count, etc.) but not for text.

2. **Template-based text augmentation** — take real phishing emails and apply controlled perturbations: synonym substitution in non-signal phrases, sender name variation, brand name swapping (PayPal → Amazon → Microsoft), subject line paraphrasing. This preserves the semantic phishing signal while increasing surface diversity.

3. **LLM-assisted generation (post-v1)** — noted in datasets.md as a future direction. For v1, stick to template augmentation. LLM-generated phishing text is harder to quality-control and introduces the risk of generating samples that are too clean (no authentication failures, no infrastructure signals) — which would teach the model wrong patterns.

**Subtype coverage requirement**: The 20k phishing samples must cover all five subtypes defined in datasets.md:
- Credential harvesting
- BEC / executive impersonation
- Malware delivery
- Invoice / payment fraud
- Redirect / landing-page phishing

BEC is the hardest — it has no links, no attachments, and relies purely on text signals. Nazario and IWSPA-AP are thin on BEC. This subtype will need the most template augmentation and will likely have the lowest model confidence in v1 (which is why BEC always routes to Analyst Review regardless of confidence — that's the right call).

---

### Junk Class

**Use: SpamAssassin hard ham + Enron external noise + synthetic generation + manual gold set**

This is the most complex construction task because no dataset natively labels Junk.

**SpamAssassin hard ham** (~250 samples): These are legitimate emails that look like spam — newsletters, mailing list traffic, promotional content. They're the closest thing to Junk in any public dataset. Use all of them as Junk seed samples.

**Enron external non-business mail**: The Enron corpus has ~500k emails, but the vast majority are internal corporate communication — useless for Junk. The useful subset is external-facing mail: vendor solicitations, event invites, mailing list subscriptions, B2B outreach. Estimate ~2,000–5,000 emails qualify after filtering. These become Junk candidates.

**Synthetic generation**: The datasets.md plan calls for template-based synthetic Junk. This is necessary — organic Junk sources alone won't reach 15k. Templates should cover: consulting solicitations, webinar invites, reward point offers, SaaS trial promotions, B2B vendor outreach. Vary sender names, company names, offer details. Synthetic samples go through the same exclusion filters as organic samples (no credential requests, no impersonation, no financial fraud context).

**Manual gold set (500–1,000 samples)**: This is the validation anchor. Without it, you can't trust the weak-supervision labels. The gold set should be reviewed by two independent annotators with Cohen's Kappa > 0.75 before any Junk training proceeds. This is non-negotiable — the Junk class is the most ambiguous and the most likely to have label noise.

**Junk class promotion**: As noted in datasets.md, Junk starts as a weak-supervision class and gets promoted to a fully learned class once ≥5,000 analyst-verified labels accumulate. In v1, the Junk class is the least reliable of the three — the model should be expected to route more Junk-adjacent emails to Analyst Review, and that's correct behavior.

---

## Final Composition Targets

| Class | Organic Sources | Augmented/Synthetic | Total Target |
|---|---|---|---|
| Spam | ~118k available → downsample | None needed | ~20,000 |
| Junk | ~3,000–7,000 organic | ~8,000–12,000 synthetic | ~15,000 |
| Phishing | ~5,000–8,000 organic | ~12,000–15,000 augmented | ~20,000 |
| **Total** | | | **~55,000** |

55k is large enough to train a fine-tuned RoBERTa with meaningful generalization. It's not enormous, but quality and diversity matter more than raw count here. A 500k dataset with 80% legacy spam from 2007 would produce a worse model than a 55k dataset stratified across eras, sources, and subtypes.

---

## Stratification: The Most Important Rule

Raw counts don't guarantee generalization. The sampling manifest must enforce:

**Era distribution (per class):**
- Legacy (pre-2010): ≤ 30% of any class
- Mid (2010–2018): ~40%
- Recent (2018–present): ≥ 30%

The problem: most public datasets are legacy or mid-era. Recent samples are scarce. This is where synthetic augmentation and PhishTank (continuously updated) become critical for the phishing class. For spam, TREC 2007 is legacy but large — cap its contribution at 30% of the spam class.

**Phishing subtype distribution:**
Each of the five subtypes should represent at least 10% of the phishing class (~2,000 samples each). BEC will be the hardest to hit — accept 8–10% for BEC in v1 and compensate with the always-route-to-review rule.

**Source diversity:**
No single dataset should contribute more than 40% of any class. This prevents the model from learning dataset-specific artifacts (e.g., Enron-specific email formatting patterns) instead of generalizable signals.

---

## What Not to Use

**Ling-Spam for training**: Too small, too domain-specific. Reserve for cross-dataset generalization testing only — train on everything else, test on Ling-Spam to verify the model generalizes to unseen sources.

**UCI SMS Spam**: Wrong modality. No headers, no HTML, no authentication signals. Would teach the model SMS-specific patterns that actively hurt email classification.

**Raw PhishTank as training emails**: PhishTank provides URLs, not full emails. Using URLs alone as training samples would produce a URL classifier, not an email classifier. Use PhishTank to enrich existing phishing samples and to validate URL features, not as standalone training data.

**Unaudited Kaggle data**: Only use after the 500-sample quality audit passes the Kappa threshold. If it fails, exclude entirely rather than risk label noise in the phishing class — label noise in phishing is worse than having fewer samples, because it directly degrades recall.

---

## Train / Validation / Test Split

70% / 15% / 15%, stratified by class. But with one additional constraint: **the test set should be temporally later than the training set where timestamps are available.** This is more realistic than a random split — in production, the model always sees future emails it wasn't trained on.

For cross-dataset generalization: hold out Ling-Spam entirely from training and use it as an out-of-distribution test. If the model performs well on Ling-Spam without ever training on it, that's strong evidence of generalization.

---

## The Sampling Manifest

Every training sample gets a record in the manifest:

```
source | era_bucket | subtype | label | augmented (bool) | split (train/val/test)
```

This is versioned with the model checkpoint. If a model version shows degraded phishing recall, you can inspect the manifest to see if a particular era bucket or subtype is underrepresented. Without the manifest, debugging dataset composition issues is guesswork.

---

## Summary of Key Decisions

| Decision | Reasoning |
|---|---|
| Cap spam at 20k despite 118k available | Class balance; more spam doesn't improve spam recall, it hurts phishing recall |
| Augment phishing to 20k | Organic phishing data is too scarce; augmentation is necessary, not optional |
| Construct Junk via weak supervision | No native Junk dataset exists; this is the only viable path |
| Require manual gold set before Junk training | Junk is the most ambiguous class; label noise here is highest risk |
| Exclude SMS data | Wrong modality; would introduce noise, not signal |
| Reserve Ling-Spam for OOD testing | Better used as a generalization probe than as training data |
| Enforce era stratification | Legacy-heavy training produces models that fail on modern attacks |
| Enforce subtype coverage for phishing | A model that misses BEC or invoice fraud has failed operationally |
| Version the sampling manifest | Reproducibility and debugging; without it, dataset composition is unauditable |

---

# Feature Data Plan: Attachments, URLs, Metadata, Domains, and Behavioral Signals

## The Real Input Problem

Public email corpora give you raw `.eml` / `.mbox` files. The model doesn't consume raw emails — it consumes extracted feature vectors across three encoders: text, metadata, and behavioral. The section above addressed the text side. This section covers everything else, and critically, what data exists in public corpora vs. what must be constructed or computed.

---

## What the Model Actually Consumes Per Email

### Text Encoder Input
Subject + body → tokenized → RoBERTa embeddings. Covered by existing email corpora.

### Metadata Encoder Input (10 features per email)

| Feature | Source in Raw Email | Availability in Public Datasets |
|---|---|---|
| SPF result | `Received-SPF` / `Authentication-Results` header | Present if headers preserved; absent in stripped datasets |
| DKIM result | `DKIM-Signature` / `Authentication-Results` header | Present in post-2011 corpora with full headers |
| DMARC result | `Authentication-Results` header | Only in post-2015 emails — absent in all legacy datasets |
| Number of links | Parse HTML body | Directly derivable |
| Number of attachments | MIME structure | Directly derivable |
| Domain age | WHOIS at collection time | **Not in datasets — must be computed** |
| TLD risk score | Extract TLD from sender domain | Derivable with a static lookup table |
| Reply-to mismatch | `Reply-To` vs `From` headers | Directly derivable if headers preserved |
| HTML/text ratio | Parse MIME parts | Directly derivable |
| Sender reputation score | IP blocklist + domain age composite | **Not in datasets — must be computed** |

### Behavioral Encoder Input (7 features per email)

| Feature | Source | Availability |
|---|---|---|
| Sender seen before | Cross-email history within corpus | Only real in Enron; simulated for all others |
| Historical sender trust | Aggregate of past interactions | Only real in Enron |
| Communication frequency | Count of prior emails from sender | Only real in Enron |
| Typical send hour deviation | `Date` header vs. sender's historical pattern | Partially derivable from Enron; simulated elsewhere |
| First-time domain indicator | Cross-email domain history | Derivable from Enron; simulated for others |
| Similar campaign burst score | Cluster emails by content similarity | Computed at dataset construction time |
| Department targeting anomaly | Recipient metadata | Not available in public datasets — omit in v1 |

---

## The Gap: What Public Datasets Don't Provide

Public corpora give text and partial headers. They do not give:

1. **Domain age** — WHOIS data at time of sending. A 2008 email's domain may now be 18 years old, but at send time it may have been 3 days old.
2. **Sender IP reputation** — IP blocklist status at time of sending. Historical IP reputation is not preserved in corpora.
3. **Behavioral history** — Most datasets are collections of individual emails with no cross-email sender history. Enron is the only exception.
4. **DMARC results** — DMARC (RFC 7489) was published in 2015. TREC 2007, CEAS 2008, SpamAssassin, Nazario — all pre-DMARC. These will have `dmarc_result=none` by definition.
5. **Attachment content** — Datasets typically strip or omit attachments for safety/size reasons.

---

## How to Handle Each Gap

### Domain Age
At dataset construction time, query WHOIS for each unique sender domain and record registration date. Compute domain age as `(email_date - domain_registration_date)`. For synthetic and augmented samples, assign domain age explicitly: phishing samples get 1–30 days, spam/junk get 1–10 years.

**Tool**: `python-whois`. Results cached in the sampling manifest. No live WHOIS at inference time.

### Sender IP Reputation
Historical IP reputation is not recoverable for legacy datasets. Extract the sending IP from `Received` headers and check against current Spamhaus ZEN / SURBL blocklists at construction time. Imperfect for old emails but directionally correct — IPs used in known campaigns tend to remain flagged or belong to infrastructure still categorized as bulk/malicious.

For synthetic samples, assign IP reputation explicitly by label.

**Tool**: Spamhaus ZEN DNS blocklist (free for non-commercial use), SURBL. Queried once at construction time, cached.

### Behavioral History
Enron is the only source of real behavioral history. For all other datasets, behavioral features are **simulated at construction time** based on label:

- Phishing: `sender_seen_before=False`, `first_time_domain=True`, `communication_frequency=0`, `send_hour_deviation=high`
- Spam: `sender_seen_before=False`, `first_time_domain=False`, `communication_frequency=0`
- Junk: `sender_seen_before=False`, `first_time_domain=False`, `communication_frequency=0`

For Enron specifically: group emails by sender, compute actual behavioral features from the full corpus history before splitting into train/val/test.

### DMARC for Pre-2015 Data
Set `dmarc_result=none` for all pre-2015 emails. This is factually correct. The model will learn that `dmarc_result=none` is the baseline for old email, while `dmarc_result=fail` on a modern email is meaningful. Era stratification in the sampling manifest ensures this distinction is preserved.

### Attachments
Most public datasets don't include real attachments. Use what's available in MIME headers: attachment presence (bool), attachment count, MIME type declared in headers, filename if present. Actual file content analysis is not feasible on public corpus data.

For synthetic phishing samples representing the malware delivery subtype, explicitly set attachment feature flags: `has_attachment=True`, `attachment_type=macro_enabled_office`, `attachment_name_pattern=invoice_pattern`.

---

## URL Features: What Exists and What Must Be Built

The following URL features are **directly extractable** from raw email text:

- URL count
- TLD of each URL domain
- Presence of IP address as host
- Port number in URL
- URL length
- Subdomain depth
- URL shortener presence (bit.ly, tinyurl, etc.) — pattern match
- Homograph characters — requires Unicode normalization pass before detection
- Anchor text vs. href mismatch

The following require **external data at construction time**:

- **Domain age of URL domain** — same WHOIS approach as sender domain
- **PhishTank/SURBL hit** — query at construction time, cache as binary feature. Phishing emails should have PhishTank hits; spam/junk should not. This is a strong feature but must not be the only feature — the model must generalize to URLs not yet in PhishTank.

**PhiUSIIL dataset**: URL-only dataset (no full emails). Use it to validate the URL feature extraction pipeline, not as training samples for the email classifier.

---

## Domain Authentication Protocols: What Exists vs. What We Need

### Protocols Already in Production (Extract from Headers)

**SPF (Sender Policy Framework — RFC 7208, 2014)**
The sending domain publishes a DNS TXT record listing authorized sending IPs. The receiving server checks the sending IP against this record.

- Result values: `pass`, `fail`, `softfail`, `neutral`, `none`, `temperror`, `permerror`
- Source in email: `Received-SPF` header or `Authentication-Results` header
- Normalize to 5 categories for training: `pass`, `fail`, `softfail`, `none`, `error`
- Dataset availability: Present in most corpora with full headers. Absent in stripped datasets.

**DKIM (DomainKeys Identified Mail — RFC 6376, 2011)**
The sending server signs the email with a private key. The receiving server retrieves the public key from DNS and verifies the signature. Proves the email wasn't tampered with in transit.

- Result values: `pass`, `fail`, `none`, `policy`, `neutral`, `temperror`, `permerror`
- Source in email: `Authentication-Results` header, `DKIM-Signature` header
- Normalize to 3 categories: `pass`, `fail`, `none`
- Dataset availability: Present in post-2011 corpora with full headers. Absent in pre-2011 data.

**DMARC (Domain-based Message Authentication, Reporting & Conformance — RFC 7489, 2015)**
Builds on SPF and DKIM. Requires alignment — the `From` header domain must match the domain that passed SPF or DKIM. The domain owner publishes a policy (none/quarantine/reject).

- Result values: `pass`, `fail`, `bestguesspass`, `none`
- Source in email: `Authentication-Results` header
- Normalize to 3 categories: `pass`, `fail`, `none`
- Dataset availability: Only in post-2015 emails. Set to `none` for all legacy data.

**Combined authentication signal interpretation:**

| SPF | DKIM | DMARC | Interpretation | Weight |
|---|---|---|---|---|
| pass | pass | pass | Fully authenticated | Low phishing signal |
| pass | pass | fail | Alignment issue — From domain mismatch | Medium |
| pass | fail | fail | IP authorized but content tampered or wrong key | Medium-High |
| fail | fail | fail | No authentication at all | High phishing signal |
| pass | none | none | Bulk sender pattern — SPF only | Spam/Junk signal |
| none | none | none | No auth records — unverifiable | High phishing signal |

**Critical nuance**: Authentication failure does not mean phishing. Many legitimate small businesses have misconfigured email. The model must learn this from training data — Enron emails from small external vendors will often have SPF softfail or no DKIM, but they're legitimate. Authentication signals are model inputs, not hard rules.

---

### What Must Be Computed for This Project (Not Standard Headers)

**Domain Age**
Not a protocol. Computed via WHOIS at dataset construction time. See gap handling above.

**TLD Risk Score**
A static lookup table mapping TLDs to a risk tier. Must be built and versioned as a project asset.

- High risk: `.xyz`, `.top`, `.tk`, `.ml`, `.ga`, `.click`, `.gq`, `.cf` — free TLDs heavily abused for phishing infrastructure
- Medium risk: `.info`, `.biz`, `.online`, `.site`, `.website` — lower cost, higher abuse rate than legacy TLDs
- Low risk: `.com`, `.org`, `.net`, `.edu`, `.gov`, `.co.uk`, `.de`, `.fr` — established, higher registration cost, lower abuse rate

**Reply-to Mismatch**
Computed by comparing the domain in `Reply-To` header against the domain in `From` header. Binary feature. Directly extractable — no external data needed.

**Sender Reputation Score**
Composite of: IP blocklist status (Spamhaus ZEN) + domain age + DMARC policy + sending volume anomaly. Computed at dataset construction time. At inference, the individual components are the actual features — the MLP learns to combine them.

**Lookalike Domain Detection**
Computed at feature extraction time:
- Levenshtein edit distance ≤ 2 against a list of ~500 known brand domains (Microsoft, PayPal, Amazon, Google, Apple, Chase, etc.)
- Unicode normalization + homograph mapping (Cyrillic `а` → Latin `a`, etc.) before edit distance computation — edit distance alone does not catch Unicode substitutions
- Subdomain abuse detection: check if a known brand domain appears as a subdomain of the sender domain (e.g., `paypal.com.attacker.net`)

The brand domain list is a static versioned asset. Not a live lookup.

**HTML/Text Ratio**
Computed from MIME structure. Ratio of HTML content length to plain text content length. Directly extractable.

**Campaign Burst Score**
Computed across the dataset at construction time: cluster emails by content similarity (TF-IDF cosine similarity or MinHash LSH), count how many similar emails appear in a short time window. High burst = bulk campaign. At inference time this becomes a real-time sliding window signal; for training data it is approximated from the corpus.

---

## Complete Feature Vector Per Training Sample

Every training sample must have all of the following populated before training begins:

**Text features** (transformer input):
`subject`, `body_text`, `sender_display_name`, `url_token_text`

**Metadata features** (MLP input — 10 values):
`spf_result`, `dkim_result`, `dmarc_result`, `url_count`, `attachment_count`, `sender_domain_age_days`, `tld_risk_score`, `reply_to_mismatch`, `html_text_ratio`, `sender_reputation_score`

**Behavioral features** (MLP input — 7 values):
`sender_seen_before`, `historical_sender_trust`, `communication_frequency`, `send_hour_deviation`, `first_time_domain`, `campaign_burst_score`, `lookalike_domain_detected`

**Label**: `spam` | `junk` | `phishing`

**Manifest fields**: `source`, `era_bucket`, `subtype`, `augmented`, `split`

Any sample missing more than 2 metadata/behavioral features after extraction is excluded from training. Imputing zeros for missing features introduces systematic bias — imputing `spf_result=pass` when the header is absent is wrong; the correct value is `none`.

---

## Dataset Construction Order

1. Download all raw corpora (TREC, SpamAssassin, CEAS, Enron, Nazario, IWSPA-AP, Kaggle)
2. Parse all emails: extract headers, body text, MIME structure, URLs
3. Run WHOIS queries for all unique sender domains and URL domains — cache results
4. Run Spamhaus ZEN lookups for all unique sending IPs — cache results
5. Run PhishTank/SURBL lookups for all unique URLs — cache results
6. Compute derived features: reply-to mismatch, HTML/text ratio, TLD risk score, lookalike domain detection, URL structural features
7. Compute Enron behavioral history (sender frequency, first-contact, send-hour patterns)
8. Simulate behavioral features for non-Enron samples based on label
9. Apply Junk labeling rules to candidate samples; run gold set validation (Kappa > 0.75)
10. Apply stratified sampling to hit class targets with era/subtype distribution
11. Generate sampling manifest
12. Split 70/15/15 with temporal constraint where timestamps are available

Steps 3–5 are the slow ones (network I/O). Run them once, cache everything. Never re-query at training time.
