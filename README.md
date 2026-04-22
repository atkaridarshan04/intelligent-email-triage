# Spam & Phishing Email Detection

An AI-based system to automatically classify user-reported emails into three categories — **spam/junk**, **gray/bulk**, and **phishing** — to reduce manual triage effort for SOC analysts.

## Background

SOC analysts receive thousands of user-reported emails daily. Most are spam or bulk mail, not phishing. Since users aren't expected to tell the difference, everything lands in the analyst queue. This project introduces AI-based categorization to filter the noise and surface only the emails that genuinely need investigation.

## Goal

Reduce analyst false positive load by 40–50% in v1, with accuracy improving over time through an analyst feedback loop.

## Classification Output

Every reported email is classified into one of three buckets:

| Bucket | Risk | SOC Action |
|---|---|---|
| Spam / Junk | Low | None — auto-dismiss |
| Gray / Bulk | Low–Medium | Minimal review |
| Phishing | High | Full investigation |

Each classification includes a confidence score and a `manual_review` flag for borderline cases.

## Documentation

| Doc | Description |
|---|---|
| [Problem Statement](docs/problem-statement.md) | Full problem definition, objectives, and constraints |
| [Phishing Attack Evolution](docs/phishing-attacks.md) | How phishing has evolved and why spam/phishing are hard to separate |
| [AI System Design](docs/ai-solutions.md) | Model architecture, feature design, and staged implementation approach |
| [Classification Logic](docs/classification-logic.md) | Signal definitions, confidence scoring, and manual review rules per bucket |
| [Datasets](docs/datasets.md) | Public datasets used for training and validation |
| [Feedback Loop](docs/feedback-loop.md) | How analyst verdicts feed back into the model |
| [Evaluation Approach](docs/evaluation-approach.md) | Metrics, baselines, and evaluation methodology |

## Status

Currently in research and design phase. Prototype implementation in progress.

## License

[MIT](LICENSE)
