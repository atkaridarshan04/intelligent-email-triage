# Spam & Phishing Email Detection

An AI-based system to automatically classify user-reported emails and route them to one of four operational outcomes — **spam**, **junk**, **phishing**, and **analyst review** — to reduce manual triage effort for SOC analysts.

## Background

SOC analysts receive thousands of user-reported emails daily. Most are spam or bulk mail, not phishing. Since users aren't expected to tell the difference, everything lands in the analyst queue. This project introduces AI-based categorization to filter the noise and surface only the emails that genuinely need investigation.

## Goal

Reduce analyst false positive load by >50% and achieve >98% phishing recall, with accuracy improving over time through a feedback-driven continual learning pipeline.

## Design

The model is trained on **three semantic classes**: Spam, Junk, Phishing.

**Analyst Review is not a training class.** It is an operational routing state triggered at inference time when the model's confidence is insufficient to automate a decision. This keeps training data clean and makes confidence calibration reliable.

```
Model learns:     Spam | Junk | Phishing
Runtime outputs:  Spam | Junk | Phishing | Analyst Review
```

## Classification Output

Every reported email is routed to one of four operational outcomes:

| Outcome | Risk | SOC Action |
|---|---|---|
| Spam | Low | Auto-folder |
| Junk | Low–Medium | Junk route |
| Phishing | High | Immediate alert + full investigation |
| Analyst Review | Uncertain | Manual triage |

Each decision includes a calibrated 0–100 risk score and machine-readable reasoning.

## Documentation

| Doc | Description |
|---|---|
| [Problem Statement](docs/problem-statement.md) | Full problem definition, objectives, and constraints |
| [Phishing Attack Evolution](docs/phishing-attacks.md) | How phishing has evolved and why spam/phishing are hard to separate |
| [AI System Design](docs/ai-solutions.md) | Model architecture, feature design, and implementation approach |
| [Classification Logic](docs/classification-logic.md) | Signal definitions, confidence scoring, and routing rules per class |
| [Confidence & Explainability](docs/confidence-and-explainability.md) | Trust score design, routing thresholds, attribution sources, and output schemas |
| [Datasets](docs/datasets.md) | Public datasets used for training and validation |
| [Feedback Loop](docs/feedback-loop.md) | How analyst verdicts feed back into the model |
| [Evaluation Approach](docs/evaluation-approach.md) | Metrics, baselines, and evaluation methodology |

## Status

Currently in research and design phase. Prototype implementation in progress.

## License

[MIT](LICENSE)
