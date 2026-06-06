# 02 — The Dataset Explained

## What Is a Dataset?

A dataset is the collection of examples the AI learns from. Think of it like a textbook for the AI — it reads thousands of labelled examples ("this email is spam", "this email is phishing") and learns the patterns that distinguish them.

Without a good dataset, even the best AI algorithm produces bad results. The quality of the data is more important than the sophistication of the model.

## Where Our Data Came From

We used several publicly available email datasets:

| Source | What it contains | Label |
|--------|-----------------|-------|
| **TREC 2007** | ~75,000 spam emails from a public corpus | Spam |
| **SpamAssassin** | ~3,000 curated spam emails | Spam |
| **CEAS 2008** | ~40,000 spam emails | Spam |
| **Enron** | Real corporate emails (used as spam examples) | Spam |
| **Nazario** | ~2,000 real phishing emails, well-curated | Phishing |
| **IWSPA-AP** | Phishing emails including spear phishing | Phishing |
| **Kaggle Phishing** | Phishing email collection | Phishing |
| **Synthetic** | AI-generated phishing emails (to fill gaps) | Phishing |

**Why multiple sources?** No single dataset is complete. Using many sources makes the AI more robust — it learns from diverse examples rather than memorising one dataset's quirks.

## The Problem with Raw Data

Raw data is messy. Before training, we had to fix several serious problems:

### Problem 1: Cross-Split Leakage
**What it is:** The same email appearing in both the training set and the test set.

**Why it's bad:** If the AI has already "seen" a test email during training, its test score is artificially inflated. It's like giving a student the exam answers before the exam — their score doesn't reflect real ability.

**What we found:** 10 train-validation overlaps, 11 train-test overlaps, 15 validation-test overlaps.

**How we fixed it:** Hashed every email body (converted it to a unique fingerprint), then removed any email that appeared in more than one split.

### Problem 2: Augmentation Leakage
**What it is:** Synthetic (AI-generated) emails appearing in the validation and test sets.

**Why it's bad:** The validation and test sets should only contain real emails. If synthetic emails are in there, the AI's performance score is measured partly on fake data, which doesn't reflect how it will perform on real emails.

**What we found:** 90 synthetic emails in validation, 92 in test.

**How we fixed it:** Removed all synthetic emails from validation and test. Synthetic emails are only allowed in training.

### Problem 3: Source Leakage
**What it is:** The dataset source (e.g., "this came from Enron") being available as a feature the AI could use.

**Why it's bad:** In production, the AI won't know which dataset an email "came from" — that information doesn't exist for real emails. If the AI learns "Enron emails = spam", it's learning a dataset artifact, not a real spam signal.

**How we fixed it:** Removed the `source`, `augmented`, `era_bucket`, `subtype`, `attachment_type`, and `id` columns before training.

### Problem 4: Distribution Drift
**What it is:** The training set and test set having very different statistical properties.

**What we found:** Training emails had average 1.73 URLs, test emails had average 0.02 URLs. Training subjects averaged 31.7 characters, test subjects averaged 16.3 characters. The two sets looked like they came from different worlds.

**How we fixed it:** Rebuilt the splits using stratified random sampling — randomly shuffling all emails and splitting 70/15/15, ensuring each split has the same proportion of spam/phishing and the same mix of sources.

## The Final Clean Dataset

After all fixes:

| Split | Samples | Spam | Phishing |
|-------|--------:|-----:|---------:|
| Train | 15,483 | 6,909 (44.6%) | 8,574 (55.4%) |
| Validation | 3,188 | 1,480 (46.4%) | 1,708 (53.6%) |
| Test | 3,189 | 1,481 (46.4%) | 1,708 (53.6%) |
| **Total** | **21,860** | | |

**Zero cross-split leakage. Zero synthetic emails in val/test. No leaky columns.**

## What Are Train, Validation, and Test Sets?

This is a fundamental concept in machine learning:

- **Training set (70%):** The AI learns from this. It sees these emails and their labels, and adjusts itself to get better at predicting them.

- **Validation set (15%):** Used during development to check how the AI is doing. We use this to tune settings (called hyperparameters) and decide when to stop training. The AI never trains on this data, but we do use it to make decisions.

- **Test set (15%):** The final exam. The AI has never seen these emails. We only look at test set performance once, at the very end, to get an honest measure of how the AI will perform on real-world emails it's never encountered.

**Why keep them separate?** If you train and evaluate on the same data, you get an optimistic (wrong) picture of performance. The test set simulates the real world — emails the AI has never seen before.

## Known Limitations of Our Dataset

Even after cleaning, the dataset has known gaps:

1. **Sparse header features:** Most emails came from Kaggle CSV files that don't preserve email headers (sender address, reply-to, etc.). So features like "display_from_mismatch" are True for only 0.2% of emails. The AI ends up relying mostly on text content.

2. **Enron artifacts:** The Enron dataset contains company-specific words (employee names, internal system names) that appear as spam signals. These won't generalise to real-world spam.

3. **Limited recent emails:** Most public datasets are from 2007–2015. Modern phishing techniques (especially BEC — Business Email Compromise) are underrepresented.

These limitations are known and documented. They affect how well the AI generalises to modern real-world emails, which is part of why Phase 3 (transformer) is being explored.
