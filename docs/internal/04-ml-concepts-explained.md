# 04 — Machine Learning Concepts Explained

## What Is Machine Learning?

Machine learning (ML) is a way of teaching computers to make decisions by showing them examples, rather than writing explicit rules.

**Traditional programming:**
```
IF email contains "click here" AND sender is unknown → mark as phishing
```
You write the rules manually. This breaks when attackers change their language.

**Machine learning:**
```
Show the computer 15,000 labelled emails.
Let it figure out the rules itself.
```
The computer discovers patterns you might never think of — combinations of hundreds of signals that together predict phishing.

## Classification

Our task is **binary classification** — sorting emails into one of two categories: spam (0) or phishing (1).

The AI learns a **decision boundary** — an imaginary line in a high-dimensional space that separates spam from phishing. When a new email arrives, the AI checks which side of the line it falls on.

## Training

Training is the process of the AI learning from examples.

1. Show the AI an email
2. AI makes a prediction (spam or phishing)
3. Compare prediction to the correct answer
4. Calculate the error (how wrong was it?)
5. Adjust the AI's internal settings to reduce the error
6. Repeat for all 15,483 training emails
7. Repeat the whole process multiple times (called epochs)

The AI's internal settings are called **parameters** or **weights**. Training adjusts these weights until the AI makes good predictions.

## The Loss Function

The loss function measures how wrong the AI is. During training, the AI tries to minimise the loss.

We use **cross-entropy loss** — a standard loss function for classification. It penalises confident wrong predictions more than uncertain wrong predictions.

We also use **weighted loss** — phishing false negatives (missing a phishing email) are penalised more heavily than spam false negatives. This biases the AI toward catching phishing even at the cost of occasionally misclassifying spam.

## Overfitting vs Underfitting

**Overfitting:** The AI memorises the training data instead of learning general patterns. It performs great on training data but poorly on new emails.

Example: The AI learns "any email mentioning 'Vince' is spam" because Vince is a common name in the Enron training dataset. But in production, emails mentioning Vince aren't necessarily spam.

**Underfitting:** The AI is too simple to capture the patterns. It performs poorly on both training and new data.

**The goal:** Find the sweet spot — a model that generalises well to new emails it's never seen.

**How we detect overfitting:** Compare training performance to validation performance. If training accuracy is 99% but validation accuracy is 85%, the model is overfitting.

## Hyperparameters

Parameters are what the AI learns during training (the weights). Hyperparameters are settings you choose before training that control how the AI learns.

Examples:
- How many trees to build (LightGBM)
- How fast to learn (learning rate)
- How complex each tree can be (num_leaves)
- How long to train (epochs)

We tune hyperparameters using the **validation set** — try different settings, see which gives the best validation performance, use those settings for the final model.

## The Three Models We Built

### Phase 1: Logistic Regression

The simplest possible classifier. It learns a straight line (in high-dimensional space) that separates spam from phishing.

**How it works:** Each feature gets a weight. The prediction is the weighted sum of all features, passed through a sigmoid function to get a probability between 0 and 1.

**Strengths:** Fast, interpretable (you can see exactly which words push toward phishing), good baseline.

**Weaknesses:** Can only learn linear relationships. Can't capture "this word is a phishing signal only when combined with that other word."

### Phase 2: LightGBM (Gradient Boosted Trees)

A much more powerful model. It builds hundreds of decision trees, each one correcting the mistakes of the previous ones.

**How it works:**
1. Build a simple decision tree
2. Look at where it made mistakes
3. Build another tree focused on those mistakes
4. Repeat 224 times (our best iteration)
5. Final prediction = weighted sum of all 224 trees

**Strengths:** Captures nonlinear relationships and feature interactions. Fast inference. Handles sparse features well. Excellent performance on tabular data.

**Weaknesses:** Doesn't understand language semantically — it sees words as independent tokens, not as meaning.

### Phase 3: RoBERTa Transformer

A deep learning model pre-trained on billions of words of text. It understands language contextually — the same word means different things in different contexts.

**How it works:**
- RoBERTa reads the email and produces a rich numerical representation (embedding) that captures the meaning of the text
- A separate MLP (Multi-Layer Perceptron) processes the 19 structured features
- Both representations are combined (fused) and passed to a classification head

**Strengths:** Deep semantic understanding. Well-calibrated probabilities. Better at detecting subtle phishing language.

**Weaknesses:** Slow to train (hours on GPU). Complex to deploy. Higher latency.

## What Is a Neural Network?

A neural network is a type of model loosely inspired by the brain. It consists of layers of "neurons" (mathematical functions) connected together.

```
Input → [Layer 1] → [Layer 2] → [Layer 3] → Output
```

Each layer transforms the data, extracting increasingly abstract patterns. The first layer might detect individual words. The second layer might detect phrases. The third layer might detect intent.

RoBERTa is a very deep neural network with 125 million parameters, pre-trained on massive amounts of text. We fine-tune it on our email dataset — adjusting its weights slightly to specialise it for spam/phishing classification.

## What Is Fine-Tuning?

Pre-training: Train RoBERTa on billions of words from the internet. It learns general language understanding.

Fine-tuning: Take that pre-trained model and continue training it on our specific task (spam vs phishing classification) with our specific dataset.

Fine-tuning is much faster than training from scratch because the model already understands language — we're just teaching it to apply that understanding to our specific problem.

## What Is a GPU and Why Do We Need It?

A GPU (Graphics Processing Unit) is a chip originally designed for rendering graphics in video games. It turns out to be excellent for the kind of maths neural networks need — thousands of simple calculations done in parallel.

Training RoBERTa on CPU: ~10+ hours
Training RoBERTa on GPU: ~1–2 hours

For Phases 1 and 2 (LightGBM, Logistic Regression), CPU is fine — these models don't benefit from GPU. Phase 3 requires GPU.
