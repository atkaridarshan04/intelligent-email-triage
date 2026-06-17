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
| [Engineering System](docs/design/engineering-system.md) | Component design, feedback store, retraining pipeline, tech choices |
| [Scale](docs/design/scale.md) | Where v1 breaks and what to do about it |

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
| [Models Plan](docs/implementation/models.md) | Model architecture, feature set, training strategy, evaluation metrics |
| [Phase 1 Report](docs/implementation/phase1-report.md) | Logistic Regression baseline results |
| [Phase 2 Report](docs/implementation/phase2-report.md) | LightGBM results and Phase 1 comparison |
| [Phase 2b Report](docs/implementation/phase2b-report.md) | Calibration fix, threshold tuning, routing validation |
| [Phase 3 Report](docs/implementation/phase3-report.md) | Transformer experiment — all 3 runs, final analysis |
| [Final Model Decision](docs/implementation/final-model-decision.md) | Production model selection with rationale |
| [Phase 3 Gaps & Fixes](docs/implementation/phase3-gaps-and-fixes.md) | Why Phase 3 underperformed and what to fix before the next transformer run |
| [System Build Plan](docs/implementation/system-build-plan.md) | Inference pipeline, API, feedback store, retraining, demo UI, packaging — build status |
| [What's Left](docs/implementation/left.md) | Remaining tasks before the system is fully operational |

### Operations
| Doc | Description |
|---|---|
| [Feedback Loop](docs/operations/feedback-loop.md) | How analyst verdicts feed back into the model |
| [Evaluation Approach](docs/operations/evaluation-approach.md) | Metrics, baselines, and evaluation methodology |
| [API Integration Guide](docs/operations/api-integration.md) | Endpoints, request/response schemas, and SOC integration patterns |
| [Demonstration Guide](docs/operations/demonstration.md) | Demo setup, walkthrough script, and client talking points |## Status

**System build complete.** Phase 2 (LightGBM) selected as production model. All pipeline, API, feedback, retraining, demo UI, and packaging phases done (149 tests passing). One task remains before first live run: export trained model artifacts into `checkpoints/production/`. See `docs/implementation/left.md`.

## License

[MIT](LICENSE)
