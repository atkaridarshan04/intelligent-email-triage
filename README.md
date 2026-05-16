# Intelligent Email Triage

An AI-assisted SOC triage system for user-reported suspicious emails. Classifies reported emails as **Spam** or **Phishing**, and routes uncertain cases to **Analyst Review**.

## Background

SOC analysts receive large volumes of user-reported suspicious emails daily. Users are not expected to distinguish spam from phishing — everything lands in the analyst queue. This project introduces AI-based triage to filter low-risk nuisance emails and rapidly surface likely malicious threats, reducing analyst workload while keeping humans in the loop for uncertain cases.

## Goal

Reduce analyst false-positive load by >50% and achieve >98% phishing recall through a conservative human-in-the-loop triage assistant.

## Design

The model is trained on **two semantic classes**: Spam and Phishing.

**Analyst Review is not a training class.** It is an operational routing state triggered at inference time when the model's confidence is insufficient to automate a decision.

```
Model learns:     Spam | Phishing
Runtime outputs:  Spam | Phishing | Analyst Review
```

## Classification Output

Every reported email is routed to one of three operational outcomes:

| Outcome | Risk | SOC Action |
|---|---|---|
| Spam | Low | Auto-suppress |
| Phishing | High | Immediate escalation + investigation |
| Analyst Review | Uncertain | Manual triage |

## Documentation

### Design
| Doc | Description |
|---|---|
| [Problem Statement](docs/design/problem-statement.md) | Problem definition, objectives, and constraints |
| [AI System Design](docs/design/ai-solutions.md) | Model architecture, feature design, and implementation approach |
| [Classification Logic](docs/design/classification-logic.md) | Signal definitions, confidence scoring, and routing rules |
| [Confidence & Explainability](docs/design/confidence-and-explainability.md) | Trust score design, routing thresholds, and output schemas |
| [Project Structure](docs/design/project-structure.md) | Folder structure and module responsibilities |

### Research
| Doc | Description |
|---|---|
| [Phishing Attack Types](docs/research/phishing-attacks.md) | Attack patterns this system detects and their signal characteristics |
| [Datasets](docs/research/datasets.md) | Public datasets used for training and validation |

### Implementation
| Doc | Description |
|---|---|
| [Dataset Construction Plan](docs/implementation/dataset-plan.md) | Dataset sourcing, enrichment, augmentation, and construction order |
| [Parallel Track Split](docs/implementation/dataset-parallel-tracks.md) | Track A / Track B work split, shared contract, and dependency map |

### Operations
| Doc | Description |
|---|---|
| [Feedback Loop](docs/operations/feedback-loop.md) | How analyst verdicts feed back into the model |
| [Evaluation Approach](docs/operations/evaluation-approach.md) | Metrics, baselines, and evaluation methodology |

## Status

Research and design phase complete. Dataset construction in progress.

## License

[MIT](LICENSE)
