# 08 — Phase 2b Results Explained

## What Phase 2b Was

Phase 2b is not a new model — it's post-processing on top of Phase 2's LightGBM model. It has three goals:
    
1. Try to fix the calibration problem with a better technique (temperature scaling)
2. Find the optimal classification threshold
3. Validate the routing system end-to-end

## Temperature Scaling — A Better Calibration Attempt

### What Is Temperature Scaling?

Temperature scaling takes the model's raw probability outputs and adjusts them using a single number called the temperature `T`.

**The formula:**
```
calibrated_probability = sigmoid(logit(raw_probability) / T)
```

- `logit` converts a probability (0–1) to a log-odds value
- Dividing by T stretches or compresses the distribution
- `sigmoid` converts back to a probability

**If T > 1:** Probabilities move toward 0.5 (less confident)
**If T < 1:** Probabilities move toward 0 and 1 (more confident)
**If T = 1:** No change

### What We Found

Optimal temperature: **T = 1.1394** — very close to 1.0. The raw LightGBM probabilities are already so extreme (near 0 and 1) that even a small temperature barely moves them.

| Method | ECE | Brier Score |
|--------|-----|-------------|
| Platt scaling (Phase 2) | 0.4470 | 0.0207 |
| Temperature scaling (Phase 2b) | **0.4455** | **0.0191** |
| Target | **< 0.05** | — |

Temperature scaling is marginally better but **both methods completely fail the ECE target**. The calibration problem cannot be fixed with post-hoc methods on LightGBM + TF-IDF. See `10-calibration-deep-dive.md` for the full explanation.

## Threshold Sweep — Finding the Optimal Operating Point

### What Is a Classification Threshold?

The model outputs a probability between 0 and 1. The threshold is the cutoff: above it = phishing, below it = spam.

Default threshold: 0.5. You can change this to trade off recall vs precision:
- **Lower threshold (e.g., 0.3):** Catch more phishing (higher recall) but flag more spam as phishing (lower precision)
- **Higher threshold (e.g., 0.7):** Fewer false alarms but miss more phishing

### The Sweep Results

| Threshold | Phishing Recall | Spam Precision | F1 |
|-----------|----------------|----------------|-----|
| 0.05 | 99.53% | 99.41% | 0.9599 |
| 0.30 | 98.59% | 98.34% | 0.9748 |
| **0.50** | **98.13%** | **97.82%** | **0.9784** |
| 0.70 | 97.37% | 96.99% | 0.9777 |
| 0.90 | 94.50% | 93.95% | 0.9659 |

**Key finding:** Phishing recall stays above 98% from threshold 0.05 all the way to 0.50. The default 0.50 is optimal — it maximises F1 while meeting the recall target. No adjustment needed.

## Routing Band Analysis

| Band | Trust Score | Count | % | Phishing Recall | FN Rate |
|------|-------------|------:|---|----------------|---------|
| Auto-classify | > 90 | 2,970 | 93.1% | **99.19%** | 0.81% |
| Auto-classify + monitor | 75–90 | 117 | 3.7% | 92.31% | 7.69% |
| Analyst Review | 55–75 | 53 | 1.7% | 75.00% | 25.00% |
| Priority Review | < 55 | 49 | 1.5% | 63.16% | 36.84% |

**FN Rate** = fraction of phishing emails the model missed within that band.

The routing system is working as designed:
- The model is most accurate when most confident (99.19% recall in the top band)
- Uncertain cases correctly route to humans (analyst review bands have lower recall — that's why humans review them)
- Only 3.2% of emails go to analysts — minimal workload

## Final Phase 2 Metrics (Temperature Calibration)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Accuracy | 97.68% | — | ✅ |
| Phishing Recall | 98.13% | > 98% | ✅ Met |
| ECE | 0.4455 | < 0.05 | ❌ |
| Auto-classify rate | 96.8% | > 50% | ✅ |
| Ph. recall (auto) | 98.92% | — | ✅ |
