# 07 — Phase 2 Results Explained

## What Phase 2 Was

Phase 2 trained **LightGBM** — a gradient boosted tree model that is significantly more powerful than Logistic Regression. This is the primary production candidate.

## Why LightGBM Is Better Than Logistic Regression

Logistic Regression draws a straight line to separate spam from phishing. LightGBM builds hundreds of decision trees that together can draw complex, curved boundaries.

**Example of what LightGBM can learn that LR cannot:**

- "High url_entropy AND brand_mention AND long body → phishing" (a combination)
- "The word 'account' is a phishing signal, but only when combined with 'verify' or 'suspended'"
- "Short emails with no URLs are more likely to be BEC phishing"

These are nonlinear interactions — patterns that only emerge when multiple features combine. LR treats every feature independently. LightGBM captures interactions.

## How LightGBM Works (Simply)

1. Start with a simple prediction (e.g., "everything is phishing")
2. Look at which emails were predicted wrong
3. Build a decision tree focused on correcting those mistakes
4. Add that tree to the ensemble
5. Repeat 224 times (our model stopped here due to early stopping)
6. Final prediction = weighted sum of all 224 trees

Each tree is small and weak on its own. Together, they're very powerful. This is called **gradient boosting** — each tree "boosts" the performance of the previous ones by focusing on their errors.

## Early Stopping

We set a maximum of 1,000 training rounds but used **early stopping** — if the validation performance doesn't improve for 50 consecutive rounds, stop training.

Our model stopped at **round 224**. This means:
- The model converged cleanly — it found a good solution without needing all 1,000 rounds
- No overfitting — if it were overfitting, it would keep improving on training data but get worse on validation

Training log:
```
[100]  val loss: 0.0845  val AUC: 0.9958
[200]  val loss: 0.0696  val AUC: 0.9968
[224]  val loss: 0.0691  val AUC: 0.9968  ← BEST, stopped here
```

## The Results

### Test Set Performance

| Metric | Phase 1 (LR) | Phase 2 (LightGBM) | Change |
|--------|-------------|---------------------|--------|
| Accuracy | 93.51% | **97.62%** | +4.11% |
| Phishing Recall | 94.38% | **98.01%** | +3.63% |
| Phishing Precision | 93.56% | **97.55%** | +3.99% |
| ROC-AUC | 0.9720 | **0.9959** | +0.0239 |
| PR-AUC | 0.9687 | **0.9959** | +0.0272 |
| Brier Score | 0.0553 | **0.0207** | −0.0346 |
| ECE | 0.4043 | 0.4455 | +0.0427 ❌ |

**Every metric improved except ECE.** The improvement is substantial — not marginal.

### What These Numbers Mean

**98.01% phishing recall** — the model catches 98.01% of phishing emails. This meets the project target of >98%. Phase 1 was at 94.4% — a 3.6 percentage point improvement.

At SOC scale (say 1,000 phishing emails per day):
- Phase 1 misses: ~56 phishing emails per day
- Phase 2 misses: ~20 phishing emails per day
- That's 36 fewer missed phishing emails every day

**97.62% accuracy** — 9.76 out of 10 emails correctly classified.

**Brier score 0.0207** — the model's probability estimates are much more accurate than Phase 1 (0.0553). The model is better at expressing how confident it is.

**ECE 0.4455** — still badly miscalibrated. Slightly worse than Phase 1. See `10-calibration-deep-dive.md` for why.

## The Routing Simulation

| Band | Count | % | vs Phase 1 |
|------|------:|---|-----------|
| Auto-classify (> 90) | 3,114 | 97.6% | +31.1% |
| Auto-classify + monitor (75–90) | 37 | 1.2% | −15.1% |
| Analyst Review (55–75) | 26 | 0.8% | −9.7% |
| Priority Analyst Review (< 55) | 12 | 0.4% | −6.3% |

**98.8% auto-classified** (up from 82.8% in Phase 1). Only 38 emails go to analyst review.

**Phishing recall within auto-classified: 98.29%** — the model is highly confident on almost everything, and when it is confident, it's right 98.29% of the time on phishing.

**Security override triggered: 614 emails** — emails where phishing probability > 0.70 AND a high-risk signal was present (typosquatting, IP literal URL, reply-to mismatch, suspicious TLD, or sender-brand mismatch). These were immediately escalated regardless of trust score.

## SHAP Analysis — What the Model Actually Uses

SHAP (SHapley Additive exPlanations) is a technique that explains which features pushed each prediction toward phishing or spam.

For the structured features (the 19 engineered features), the SHAP analysis showed:

**Most important structured features:**
1. `body_length` — longer emails lean phishing
2. `url_entropy` — more random URLs lean phishing
3. `url_count` — more URLs lean phishing
4. `sender_brand_mismatch` — brand mismatch strongly indicates phishing
5. `brand_mention` — mentioning a brand is a phishing signal (combined with mismatch)

**Near-zero importance:**
- `display_from_mismatch` (only 0.2% of emails have this)
- `has_attachment` (only 0.1% of emails have this)
- `executable_detected`, `macro_detected` (all False — zero variance)

This confirms the dataset limitation: most structured features are sparse because the dataset comes from CSV files without full email headers. The model relies heavily on text.

## Why Phase 2 Is the Production Candidate

- Meets the primary target (>98% phishing recall) ✅
- 96.8% auto-classification rate (far exceeds >50% target) ✅
- Fast inference (LightGBM is very fast — well within 300ms) ✅
- Simple deployment (single .txt model file) ✅
- SHAP explainability built in ✅
- Only failure: ECE calibration ❌

Phase 2 is production-ready for classification. The calibration issue is addressed in Phase 2b and potentially Phase 3.
