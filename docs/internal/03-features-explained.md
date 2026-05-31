# 03 — Features Explained

## What Is a Feature?

A feature is a piece of information the AI uses to make a decision. Think of it like clues a detective uses to solve a case. The AI looks at all the clues (features) together and decides: spam or phishing?

We have two types of features:

1. **Text features** — the actual words in the email (subject and body)
2. **Structured features** — specific measurable properties of the email

## Text Features

The AI reads the subject line and body of every email. But computers can't understand words the way humans do — they need numbers. So we convert text into numbers using a technique called **TF-IDF**.

### What is TF-IDF?

TF-IDF stands for Term Frequency-Inverse Document Frequency. It's a way of measuring how important a word is in a specific email compared to all emails.

- **Term Frequency (TF):** How often does this word appear in this email? If "account" appears 5 times in an email, that's a strong signal.
- **Inverse Document Frequency (IDF):** How rare is this word across all emails? Common words like "the" and "is" appear everywhere, so they're not useful signals. Rare words like "typosquatting" are more informative.

The result: each email becomes a list of thousands of numbers, one per word, representing how important each word is in that email.

**In our project:** We used 30,000–50,000 words (features) and also included pairs of consecutive words (bigrams) like "click here" and "your account" — because the combination is often more informative than individual words.

## Structured Features

These are 19 specific properties we extract from each email:

### Sender Features

| Feature | What it measures | Why it matters |
|---------|-----------------|----------------|
| `display_from_mismatch` | Does the displayed sender name not match the actual email address? | Phishing emails often show "PayPal Security" but the actual address is random@gmail.com |
| `reply_to_mismatch` | Does the Reply-To address differ from the From address? | Phishers set Reply-To to their own address so replies go to them, not the spoofed sender |
| `free_email_sender` | Is the sender using a free email provider (Gmail, Yahoo, Hotmail)? | Legitimate companies use their own domain. Phishers often use free accounts |

### URL Features

| Feature | What it measures | Why it matters |
|---------|-----------------|----------------|
| `url_count` | How many URLs are in the email? | Phishing emails often contain multiple suspicious links |
| `domain_count` | How many unique domains do the URLs point to? | Many different domains = suspicious |
| `shortened_url_present` | Does the email contain shortened URLs (bit.ly, tinyurl)? | Shorteners hide the real destination — a common phishing trick |
| `suspicious_tld_present` | Does any URL use a high-risk top-level domain (.xyz, .tk, .ml)? | These TLDs are cheap/free and heavily abused for phishing |
| `ip_literal_url` | Does any URL use a raw IP address instead of a domain name? | Legitimate services use domain names. IP addresses in URLs are a red flag |
| `url_entropy` | How random/complex are the URL strings? | Phishing URLs are often randomly generated (high entropy) |
| `typosquatting_detected` | Does any URL look like a misspelling of a known brand? | paypa1.com, arnazon.com, micros0ft.com — designed to fool people |

### Attachment Features

| Feature | What it measures | Why it matters |
|---------|-----------------|----------------|
| `has_attachment` | Does the email have an attachment? | Malware delivery phishing always has attachments |
| `executable_detected` | Is there an executable file (.exe, .bat) attached? | Executables in emails are almost always malware |
| `macro_detected` | Is there a macro-enabled Office document attached? | Macro documents are a common malware delivery method |

> Note: In our dataset, `executable_detected` and `macro_detected` are always False — the dataset doesn't contain emails with these attachments. These features contribute nothing to the current model.

### Text Statistics

| Feature | What it measures | Why it matters |
|---------|-----------------|----------------|
| `subject_length` | How many characters in the subject line? | Very short or very long subjects can be signals |
| `body_length` | How many characters in the email body? | Phishing emails tend to be longer (more elaborate social engineering) |
| `uppercase_ratio` | What fraction of letters are uppercase? | SHOUTING IN EMAILS is a spam/phishing tactic |
| `digit_ratio` | What fraction of characters are numbers? | High digit ratio can indicate spam (phone numbers, prices) |
| `punctuation_density` | How much punctuation per character? | Excessive punctuation (!!!, ???) is a spam signal |
| `link_density` | Ratio of links to words | High link density = lots of URLs relative to text = suspicious |

### Brand Features

| Feature | What it measures | Why it matters |
|---------|-----------------|----------------|
| `brand_mention` | Does the email mention a known brand (PayPal, Amazon, Microsoft, etc.)? | Phishing emails impersonate brands to gain trust |
| `sender_brand_mismatch` | Does the email mention a brand but the sender isn't from that brand's domain? | "This is PayPal" but sent from random123@gmail.com = phishing |

## Which Features Matter Most?

From our Phase 2 SHAP analysis (see `07-phase2-results-explained.md`):

**Most important structured features:**
1. `body_length` — phishing emails tend to be longer
2. `url_entropy` — phishing URLs are more random
3. `url_count` — phishing emails have more URLs
4. `sender_brand_mismatch` — strong phishing signal
5. `brand_mention` — combined with mismatch, very informative

**Text features dominate overall.** The words in the email carry more signal than the structured features, because most of our dataset comes from CSV files that don't preserve full email headers (so sender/URL features are sparse).

## Why We Dropped Some Features

Before training, we removed features that would cause problems:

| Removed Feature | Why |
|----------------|-----|
| `id` | Just an identifier, not a signal |
| `source` | Which dataset it came from — not available in production |
| `augmented` | Whether it's synthetic — not available in production |
| `split` | Which split it's in — direct leakage |
| `era_bucket` | Inconsistent across splits |
| `subtype` | Mostly empty, provenance-adjacent |
| `attachment_type` | 99.9% empty, no signal |
| `executable_detected` | All False in this dataset — zero variance |
| `macro_detected` | All False in this dataset — zero variance |
