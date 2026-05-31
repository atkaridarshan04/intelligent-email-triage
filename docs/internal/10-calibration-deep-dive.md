# 10 — Calibration Deep Dive

## The Problem in Plain English

Imagine a weather forecaster who says "70% chance of rain" every time it's going to rain. If you track their predictions over time, you'd expect it to actually rain about 70% of the times they said 70%. If it rains 95% of those times, the forecaster is underconfident. If it rains only 40% of those times, they're overconfident.

**Calibration is the same idea for our AI model.** When the model says "I'm 90% confident this is phishing", it should be right about 90% of the time. If it's right 99% of the time, the model is underconfident (it should say 99%). If it's right only 60% of the time, the model is overconfident (it's saying 90% when it should say 60%).

## What ECE Measures

ECE (Expected Calibration Error) measures the average gap between the model's stated confidence and its actual accuracy.

**How it's calculated:**
1. Group all predictions into bins by confidence (0–10%, 10–20%, ..., 90–100%)
2. For each bin, calculate: average confidence vs actual accuracy
3. ECE = weighted average of |accuracy - confidence| across all bins

**Perfect calibration:** ECE = 0 (confidence always matches accuracy)
**Our target:** ECE < 0.05
**Our result:** ECE = 0.4455

An ECE of 0.44 means the model's confidence is off by an average of 44 percentage points. That's very bad.

## Why Our Model Is Miscalibrated

### The Root Cause: Extreme Probabilities

Our LightGBM model outputs probabilities that are almost always near 0 or near 1. Very few predictions fall in the middle range (0.3–0.7).

This happens because:
1. **High-dimensional TF-IDF features** — with 30,000 word features, the model can find very clean separations between spam and phishing in the training data
2. **Gradient boosting** — each tree corrects the previous tree's mistakes, pushing predictions further toward the correct class
3. **The classes are genuinely separable** — spam and phishing really do use different language, so the model learns to be very confident

The result: the model says "99.9% phishing" or "0.1% phishing" for almost everything. Very few emails get a probability of 0.6 or 0.7.

### Why Post-Hoc Calibration Can't Fix It

**Platt scaling** fits a sigmoid function: `calibrated = sigmoid(a × raw + b)`

Our Platt fit: `a = 8.78, b = -4.58`

The `a = 8.78` is extremely steep — it means the raw probabilities are already so extreme that even a steep sigmoid can't spread them out into a well-calibrated range.

**Temperature scaling** divides the log-odds by T: `calibrated = sigmoid(logit(raw) / T)`

Our optimal T = 1.1394 — barely above 1.0. The raw probabilities are so extreme that even dividing by 1.14 barely moves them.

**The fundamental problem:** Both methods try to remap a distribution that's already at the extremes. You can't meaningfully calibrate a distribution where 95% of values are above 0.99 or below 0.01.

## Does This Actually Matter?

This is the key question. The answer is: **it matters for some things, not for others.**

### Where It Doesn't Matter (Routing Works Fine)

The routing system uses trust score thresholds (> 90, 75–90, 55–75, < 55) to decide whether to auto-classify or send to analysts.

Because the model's probabilities are extreme, almost everything gets a very high trust score. 93.1% of emails get trust > 90. The routing outcome is correct — the model is genuinely very confident on most emails, and it's right 99.19% of the time on phishing in that band.

The miscalibration doesn't change the routing outcome because the model's discrimination is so strong.

### Where It Does Matter

**1. Analyst-facing confidence scores**
When an analyst sees "Model confidence: 94%", that number should mean something. With ECE = 0.44, it doesn't. The analyst can't trust the confidence score as an absolute probability.

**2. Threshold stability over time**
As email patterns evolve, the optimal threshold might need to change. With good calibration, you can reason about thresholds in terms of probabilities ("set threshold at 0.7 to achieve 99% recall"). With bad calibration, threshold tuning is empirical guesswork.

**3. Feedback loop integration**
When analysts correct the model's mistakes, their verdicts should be weighted by the model's confidence. With bad calibration, confidence weights are meaningless.

**4. Risk scoring**
If you want to say "this email has a 73% probability of being phishing", that statement needs to be accurate. With ECE = 0.44, it's not.

## Why Phase 3 Should Fix It

RoBERTa operates differently from LightGBM + TF-IDF:

1. **Dense semantic space** — instead of 30,000 sparse word features, RoBERTa produces 768 dense numbers representing the email's meaning. The boundary between spam and phishing in this space is more gradual.

2. **Softmax output** — RoBERTa's final layer uses softmax, which naturally produces probabilities that sum to 1 and are more spread across the 0–1 range.

3. **Cross-entropy training** — the training objective directly optimises the probability estimates to be accurate, not just to classify correctly.

4. **Dropout regularisation** — during training, random neurons are turned off, preventing the model from becoming overconfident.

These properties together tend to produce well-calibrated probabilities. Transformers are known to be better calibrated than gradient boosted trees on text tasks.

## What "Good Calibration" Would Look Like

A well-calibrated model's calibration curve would look like a diagonal line:

```
Actual accuracy
1.0 |                    /
    |                  /
0.8 |                /
    |              /
0.6 |            /
    |          /
0.4 |        /
    |      /
0.2 |    /
    |  /
0.0 |/___________________
    0.0  0.2  0.4  0.6  0.8  1.0
         Predicted confidence
```

Our current model's curve is far from this diagonal — it's compressed at the extremes, showing that the model is overconfident across the board.

## Summary

| Question | Answer |
|----------|--------|
| What is calibration? | How well confidence scores match actual accuracy |
| What is ECE? | Average gap between confidence and accuracy |
| Our ECE | 0.4455 (target < 0.05) |
| Why is it bad? | LightGBM + TF-IDF pushes probabilities to extremes |
| Can post-hoc methods fix it? | No — Platt and temperature scaling both fail |
| Does it affect routing? | Not in practice — routing works correctly |
| Does it matter? | Yes — for confidence scores, threshold stability, feedback loop |
| How to fix it? | Phase 3 transformer — expected to produce well-calibrated probabilities |
