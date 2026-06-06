# 09 — Phase 3 Explained

## What Is Phase 3?

Phase 3 builds a **hybrid transformer model** — the most sophisticated architecture in the project. It combines:

1. **RoBERTa** — a transformer that deeply understands language
2. **MLP** — a small neural network for the 19 structured features
3. **Fusion layer** — combines both into a single prediction

This is the "future-state architecture" described in the design documents. It was always intended as exploratory — only built if Phase 2 wasn't good enough.

## What Is a Transformer?

A transformer is a type of neural network that reads text and understands the meaning of words in context.

**The key difference from TF-IDF:**

TF-IDF treats words as independent tokens. It counts how often "account" appears but doesn't know whether "account" means "bank account" (phishing signal) or "account for the delay" (not a signal).

A transformer reads the whole sentence and understands context:
- "Please verify your account immediately" → phishing signal
- "I'll account for the missing funds" → not a phishing signal

Same word, completely different meaning. Transformers understand this. TF-IDF doesn't.

## What Is RoBERTa?

RoBERTa (Robustly Optimised BERT Pretraining Approach) is a transformer model developed by Facebook AI. It was trained on 160GB of text from the internet — books, Wikipedia, news articles, web pages.

After this pre-training, RoBERTa has a deep understanding of English language. It knows grammar, context, meaning, and even some world knowledge.

We take this pre-trained model and **fine-tune** it on our email dataset — teaching it to apply its language understanding specifically to spam vs phishing classification.

**RoBERTa has 125 million parameters** — 125 million numbers that encode its understanding of language. Fine-tuning adjusts these slightly for our task.

## The Architecture

```
Email subject + body text
        ↓
RoBERTa tokenizer (converts text to numbers)
        ↓
RoBERTa encoder (125M parameters, understands language)
        ↓
[CLS] embedding (768 numbers representing the email's meaning)
        ↓
                                    19 structured features
                                            ↓
                                    MLP encoder (3 layers)
                                            ↓
                                    64-number representation
        ↓                                   ↓
        └──────────── Fusion (concatenate) ─┘
                              ↓
                    832-number combined representation
                              ↓
                    Classification head (2 outputs)
                              ↓
                    Spam probability / Phishing probability
```

## What Is an MLP?

MLP stands for Multi-Layer Perceptron — a simple neural network. It takes the 19 structured features and transforms them through 3 layers of neurons, producing a 64-number representation.

Each layer applies a mathematical transformation and a non-linearity (ReLU function), allowing it to learn complex patterns in the structured features.

## Why Combine Both?

Text features (RoBERTa) and structured features (MLP) capture different aspects of an email:

- **RoBERTa** captures: language, intent, social engineering patterns, brand impersonation in text
- **MLP** captures: URL structure, sender mismatches, attachment presence, statistical text properties

Together they're more powerful than either alone. A phishing email might have subtle language AND suspicious URLs — the model sees both signals.

## Why Phase 3 Is Expected to Fix Calibration

RoBERTa uses a **softmax** output layer, which naturally produces well-calibrated probabilities. The training objective (cross-entropy loss) directly optimises the probability estimates to be accurate.

LightGBM + TF-IDF pushes probabilities to extremes because the high-dimensional sparse space makes classes appear very separable. RoBERTa operates in a dense semantic space where the boundary between spam and phishing is more gradual — producing more nuanced probability estimates.

## Training Details

- **3 epochs** (passes through the full training set)
- **AdamW optimiser** with weight decay (prevents overfitting)
- **Linear warmup + cosine decay** learning rate schedule (starts slow, peaks, then gradually decreases)
- **Weighted cross-entropy loss** — phishing false negatives penalised 1.5× more than spam false negatives
- **Gradient clipping** — prevents training instability
- **Early stopping** based on validation phishing recall

## What We're Looking For in Phase 3 Results

| Criterion | Threshold | Why |
|-----------|-----------|-----|
| ECE | < 0.10 (acceptable), < 0.05 (target) | The main reason we're building Phase 3 |
| Phishing Recall | ≥ 98.5% | Must maintain or improve on Phase 2 |
| Inference latency | < 300ms | Production requirement |
| Accuracy | ≥ 98% | Overall quality |

**If Phase 3 meets all three high-priority criteria → it replaces Phase 2 as the production model.**

**If Phase 3 fails any high-priority criterion → Phase 2 remains the production model.**

## The Risk

Phase 3 is more complex and slower than Phase 2:

- Training takes 1–2 hours on GPU (vs minutes for LightGBM)
- Inference is slower (transformer forward pass vs tree lookup)
- Deployment is more complex (PyTorch model vs single .txt file)
- Explainability is harder (Integrated Gradients vs SHAP)

If the calibration improvement is marginal (ECE goes from 0.44 to 0.35 but not below 0.10), the added complexity isn't worth it and Phase 2 remains the production model.
