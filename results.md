## Track A

> Dataset is built and structurally sound. Here's the honest assessment:

What's good:
- 21,394 total records, exactly 70/15/15 split ✅
- Train: 7,000 spam + 7,975 phishing — both within target ranges ✅
- 9 distinct sources, 6 phishing sources ✅
- No empty bodies, no empty labels, zero duplicate IDs ✅
- All 31 schema columns present ✅
- No single source exceeds 40% of either class ✅

Two things to be aware of before training:

1. Era distribution is incomplete. 44% of spam and 65% of phishing have era_bucket='' (unknown) — meaning most Kaggle CSV sources have no 
date metadata, so they couldn't be bucketed. The recent era bucket is entirely absent. The dataset plan requires recent >= 30%. This won't 
be fixable with the current organic sources — it's the gap that Track B synthetic augmentation is supposed to fill.

2. Structured feature sparsity. URL features (29.7% non-zero), sender mismatch (0.2%), attachment (0.1%) are low. This is expected — most 
Kaggle CSVs don't have sender/header/attachment data. The model will lean heavily on text features and brand signals. Again, this is a 
known limitation of organic-only data; the structured feature columns will become more useful once real .eml sources with full headers are 
added.

Neither of these blocks training — the quality gates passed and the dataset is valid. They're just known gaps to track going into model 
evaluation.


-----------------

What's fully met:
- 70/15/15 split ✅
- Spam: 7K train, Phishing: 8.4K train — both within targets ✅
- 7 phishing sources ✅
- Synthetic distributed across all splits (2.8% each) ✅
- No duplicate IDs, no empty labels ✅

Two gaps that remain — both are dataset-level limitations, not bugs:

1. recent era is 5.1% of phishing, 0% of spam — target is ≥30%. The synthetic generator only produced 5,450 samples total, and the sampler's
25% synthetic cap + 40% source cap means only ~600 synthetic slots are available per class. To hit 30% recent, you'd need ~3,600 recent 
phishing samples, which would push synthetic to ~31% — over the cap. This is the fundamental tension the dataset plan acknowledged: "Recent 
samples are scarce. This is where synthetic augmentation becomes critical." Hitting the era target properly requires either relaxing the 
synthetic cap for the recent bucket specifically, or generating more varied synthetic templates to avoid the source cap kicking in.

2. Subtype coverage is 5% of phishing — each subtype is well under the 10% target. Same root cause: the sampler can only take ~600 synthetic
phishing total before hitting the cap, spread across 9 subtypes = ~67 each.

Recommendation: These gaps are acceptable for a v1 model. The model will train and produce results. The subtype and era gaps mean it will 
be weaker on modern BEC and recent credential-harvesting patterns — which is exactly why the design routes low-confidence cases to Analyst 
Review. You can revisit synthetic volume after seeing where the model's recall breaks down in evaluation.

Ready to move to training when you are.