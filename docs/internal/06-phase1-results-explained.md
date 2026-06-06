# 06 — Phase 1 Results Explained

## What Phase 1 Was

Phase 1 built the simplest possible model — **Logistic Regression** — to establish a baseline. The goal wasn't to build the best model, but to answer: "Can this problem even be solved with classical ML? What's the floor?"

Think of it like building a rough prototype before the final product. It tells you if you're on the right track.

## What We Built

**Text processing:** We converted every email's subject and body into a numerical representation using TF-IDF (see `03-features-explained.md`). We used 50,000 word features including pairs of words (bigrams like "click here", "your account").

**Structured features:** We added 19 engineered features (URL counts, sender mismatches, etc.) and scaled them (divided by their standard deviation) because Logistic Regression requires features to be on similar scales.

**Combined feature matrix:** 50,019 features per email. The matrix for 15,483 training emails is enormous — but most values are zero (sparse), so it's stored efficiently.

**Training:** Logistic Regression with SAGA solver (efficient for large sparse data), 1,000 max iterations.

**Calibration:** After training, we applied Platt scaling on the validation set to try to make the probability outputs more accurate.

## The Results

### Test Set Performance

| Metric | Value |
|--------|-------|
| Accuracy | 93.51% |
| Phishing Recall | 94.38% |
| Phishing Precision | 93.56% |
| ROC-AUC | 0.9720 |
| PR-AUC | 0.9687 |
| Brier Score | 0.0553 |
| ECE | 0.4043 |

### What These Numbers Mean

**93.51% accuracy** — the model gets 9 out of 10 emails right. For a simple baseline, this is strong.

**94.38% phishing recall** — the model catches 94.38% of phishing emails. It misses 5.62%. The project target is >98%, so this doesn't meet the target — but it's a solid baseline.

**ROC-AUC 0.9720** — if you randomly pick one phishing and one spam email, the model ranks the phishing one higher 97.2% of the time. Very good discrimination.

**ECE 0.4043** — the model's confidence scores are badly miscalibrated. When it says "90% confident", it's not actually right 90% of the time. This is a serious problem for the routing system.

## The Routing Simulation

We simulated how the routing system would work with this model:

| Band | Count | % |
|------|------:|---|
| Auto-classify (trust > 90) | 2,122 | 66.5% |
| Auto-classify + monitor (75–90) | 519 | 16.3% |
| Analyst Review (55–75) | 334 | 10.5% |
| Priority Analyst Review (< 55) | 214 | 6.7% |

**82.8% of emails auto-classified.** Within those, phishing recall is 97.89%.

This means: the model is confident enough to auto-route 82.8% of emails, and within those it catches 97.89% of phishing. The remaining 17.2% go to analysts.

## What the Top Features Tell Us

The model learned these as the strongest phishing signals:

| Feature | Coefficient | What it means |
|---------|-------------|---------------|
| account | +2.86 | Phishing emails often say "your account" |
| click | +1.75 | "Click here" is a classic phishing phrase |
| bank | +1.63 | Financial phishing is common |
| your account | +1.53 | Bigram — even stronger signal |
| click here | +1.49 | Bigram — very strong phishing signal |
| body_length | +1.14 | Phishing emails tend to be longer |

And the strongest spam signals:

| Feature | Coefficient | What it means |
|---------|-------------|---------------|
| enron | -1.54 | Enron dataset artifact — not a real signal |
| vince | -1.04 | Enron employee name — dataset artifact |
| ect | -1.16 | Enron internal system name — dataset artifact |
| sender_brand_mismatch | -1.34 | Spam has brand mismatches (real signal) |
| link_density | -1.21 | Spam has high link density (real signal) |

**Problem spotted:** The model learned Enron-specific words as spam signals. In production, emails mentioning "Enron" or "Vince" aren't necessarily spam — the model is learning dataset identity, not real spam patterns.

## What Phase 1 Proved

1. ✅ Classical ML can solve this problem — 93.5% accuracy is strong
2. ✅ The minimum performance floor is ~94% phishing recall
3. ✅ Text features dominate — words in the email are the strongest signals
4. ❌ Calibration is broken — ECE 0.40, routing thresholds can't be trusted
5. ❌ Phishing recall (94.4%) doesn't meet the >98% target

**Conclusion:** Phase 1 is a good baseline but not good enough for production. Phase 2 is needed.
