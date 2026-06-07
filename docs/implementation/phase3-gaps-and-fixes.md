# Phase 3 — Gaps and Suggested Fixes

**Date:** 2026-06-07
**Context:** Phase 3 (RoBERTa+MLP) was outperformed by Phase 2 (LightGBM) on every classification
metric. This document records the specific reasons why and what would need to change for a
transformer to be the right production model at scale.

The central premise: on a large, real-world dataset a transformer is always more generalisable.
The Phase 3 experiment did not disprove that. It demonstrated that the current dataset is
not yet at the scale where a transformer can express that advantage.

---

## Gap 1 — Dataset too small for 125M parameters

**What happened:** 15,483 training examples against 125M trainable parameters. The model
cannot learn a reliable decision boundary at this scale. Fine-tuning RoBERTa requires the
gradient signal from many more diverse examples to meaningfully shift the pre-trained weights
toward the target task without collapsing into noise.

LightGBM with 30k TF-IDF features is better matched to 15k samples. Tree models generalise
well at this scale; transformers do not.

**Evidence:** Validation recall plateaued at ~97% across all three runs regardless of
configuration. Training loss oscillated rather than converging. This is the signature of a
data-starved fine-tune.

**Fix:**
- Target ≥ 100k training examples before re-running Phase 3.
- Primary sources: production analyst-reviewed emails (post-deployment), additional public
  phishing corpora (PhishTank, OpenPhish dumps, APWG eCrime datasets), and augmentation of
  borderline cases flagged by the routing system.
- Freeze the RoBERTa encoder for the first 1–2 epochs and only train the classification head.
  Once the head has stabilised, unfreeze the top 4–6 transformer layers and continue with a
  lower LR (5e-6). Fine-tuning all 125M parameters from epoch 1 on a small dataset wastes
  capacity and destabilises training.

---

## Gap 2 — Mixup applied inconsistently

**What happened:** The `mixup_batch` function blends structured features and soft-labels but
cannot blend tokenised text sequences. The model receives a mixed structured vector and a
blended label, but the text input is entirely from one sample. This produces an incoherent
training signal: the label says "60% phishing, 40% spam" but the text is purely phishing.
The model cannot learn to express intermediate confidence from contradictory supervision.

This likely explains why Run 2 (mixup enabled) had the worst auto-classify rate (63.6%) —
the routing system correctly identified that the model's probabilities were unreliable.

**Fix — Option A (minimal):** Disable input mixup entirely. Apply label smoothing only.
This is what Run 3 tested, and it was cleaner than Run 2. The theoretical ECE benefit of
mixup requires consistent blending across all modalities; half-mixup is worse than none.

**Fix — Option B (correct):** Apply mixup in the RoBERTa embedding space rather than token
space. After the RoBERTa encoder produces CLS embeddings, interpolate between two CLS
vectors before the fusion layer.

```python
def mixup_embeddings(cls_a, cls_b, struct_a, struct_b, labels_a, labels_b, lam):
    cls_mixed    = lam * cls_a    + (1 - lam) * cls_b
    struct_mixed = lam * struct_a + (1 - lam) * struct_b
    labels_mixed = lam * labels_a + (1 - lam) * labels_b
    return cls_mixed, struct_mixed, labels_mixed
```

This is consistent — text, structured features, and labels are all blended — and does not
require modifying the tokeniser or input pipeline. The forward pass splits into two stages:
encoder (produces CLS embeddings) and classifier head (operates on mixed embeddings).

---

## Gap 3 — ECE is a dataset property, not a model property

**What happened:** ECE ≈ 0.39–0.45 across all three model families (LR, LightGBM, RoBERTa).
Label smoothing moved it from 0.40 to 0.39 — statistically negligible. The dataset is too
cleanly separable: spam and phishing use sufficiently distinct vocabulary that any model
becomes overconfident. There are very few genuinely ambiguous examples to teach the model
to express uncertainty.

**Fix:** The only real fix is data. Ambiguous examples — emails that a model is right to
be uncertain about — must enter the training set. These do not exist in public datasets
because public datasets are curated for clean labels.

The source is the production routing system itself. Emails routed to Analyst Review are
by definition the ambiguous cases. After deployment:

1. Collect all analyst-reviewed emails with their verdicts.
2. Add them to the training set with hard labels (analyst verdict).
3. Retrain with label smoothing (ε=0.1). With real ambiguous examples present, smoothing
   will have something to work with and ECE will improve meaningfully.
4. Target ≥ 5,000 analyst-reviewed examples before expecting ECE < 0.10.

This is a feedback loop task, not a training configuration task.

---

## Gap 4 — No layer-wise learning rate decay

**What happened:** All layers of RoBERTa were trained with the same LR (2e-5 in Run 1,
1e-5 in Runs 2–3). Pre-trained transformer layers should be fine-tuned at progressively
lower rates the deeper they are — earlier layers encode general language representations
that should change minimally, while later layers and the classification head adapt most.
Using a uniform LR across all layers risks catastrophic forgetting of the pre-trained
representations.

**Fix:** Apply layer-wise LR decay (LLRD). A standard multiplier is 0.9 per layer from
the classification head down to the embedding layer.

```python
def get_layerwise_optimizer(model, base_lr=2e-5, decay=0.9):
    params = []
    # Classification head and fusion — full LR
    params.append({"params": model.classifier.parameters(), "lr": base_lr})
    params.append({"params": model.struct_encoder.parameters(), "lr": base_lr})
    # RoBERTa layers — decaying LR from top to bottom
    layers = list(model.roberta.encoder.layer)
    for i, layer in enumerate(reversed(layers)):
        lr = base_lr * (decay ** (i + 1))
        params.append({"params": layer.parameters(), "lr": lr})
    # Embeddings — lowest LR
    params.append({"params": model.roberta.embeddings.parameters(), "lr": base_lr * (decay ** len(layers))})
    return torch.optim.AdamW(params, weight_decay=0.01)
```

---

## Gap 5 — No evaluation of domain-shift robustness

**What happened:** All three runs were evaluated purely on held-out test set accuracy and
recall. There was no analysis of whether the transformer generalises better to attack
subtypes underrepresented in training (BEC, spear phishing, lookalike domains). This was
the theoretical motivation for Phase 3 — contextual understanding of subtle phishing — but
it was never directly tested.

**Fix:** Add a stratified evaluation breakdown by attack subtype using the
`sampling_manifest.jsonl` metadata. Compare LightGBM vs transformer recall per subtype.
If the transformer is meaningfully better on BEC and spear phishing (even if overall recall
is lower), that is a real signal — it justifies keeping the transformer in the architecture
for the hard cases even while LightGBM handles easy classification.

A potential production approach: a two-stage router where LightGBM handles high-confidence
cases (reducing cost and latency) and the transformer is invoked only for uncertain cases.
This is only worth building if subtype analysis confirms the transformer is genuinely better
on the hard subtypes.

---

## Gap 6 — No head+tail truncation for long emails

**What happened:** The tokeniser was configured with `truncation=True` and `max_length=512`.
This truncates from the tail — long emails lose their ending. Email bodies often place
the malicious call-to-action (phishing link, urgent instruction) at the end of a long
preamble. Tail truncation discards exactly the signal that differentiates phishing.

**Fix:** Implement explicit head+tail retention before tokenisation. Keep the first 384
tokens and the last 128 tokens, dropping the middle.

```python
def head_tail_text(text, tokenizer, max_len=512, head=384, tail=128):
    tokens = tokenizer.tokenize(text)
    if len(tokens) <= max_len:
        return text
    kept = tokens[:head] + tokens[-tail:]
    return tokenizer.convert_tokens_to_string(kept)
```

Apply this in `build_text` before constructing the dataset. The current code appended the
subject with `</s>` but relied entirely on the tokeniser's default truncation, losing the
email tail.

---

## Summary

| Gap | Impact on Phase 3 | Fix complexity |
|-----|--------------------|----------------|
| Dataset too small (15k vs 125M params) | Primary cause of underperformance | Requires post-deployment data collection |
| Inconsistent mixup (text not blended) | Training instability, poor calibration | Embedding-space mixup — medium effort |
| ECE is a dataset problem | All models fail ECE equally | Requires analyst-reviewed ambiguous examples |
| No layer-wise LR decay | Suboptimal fine-tuning, possible forgetting | Low effort — 20 lines of code |
| No subtype breakdown | Transformer's real advantage never measured | Low effort — use existing manifest metadata |
| Tail truncation discards phishing signals | Missed end-of-email CTAs | Low effort — head+tail function |

Gaps 4, 5, and 6 can be fixed immediately in the next training run at minimal cost.
Gaps 1, 2, and 3 all resolve to the same root cause: the dataset needs to grow through
the feedback loop before Phase 3 can compete with — let alone beat — Phase 2.

The transformer is the right long-term architecture. The conditions for it to win are not
yet present.
