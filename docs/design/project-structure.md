# Project Structure

## Folder Layout

```text
intelligent-email-triage/
│
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
│
├── configs/
│   ├── base.yaml
│   ├── train.yaml
│   ├── inference.yaml
│   └── thresholds.yaml
│
├── data/
│   ├── raw/
│   │   ├── spamassassin/
│   │   ├── trec/
│   │   ├── ceas/
│   │   ├── nazario/
│   │   └── phishing/
│   │
│   ├── interim/
│   │   ├── parsed_emails/
│   │   ├── cleaned/
│   │   └── deduplicated/
│   │
│   ├── processed/
│   │   ├── train.parquet
│   │   ├── valid.parquet
│   │   ├── test.parquet
│   │   └── sampling_manifest.parquet
│   │
│   └── feedback/
│       └── analyst_labels/
│
├── notebooks/
│   ├── eda.ipynb
│   ├── feature_analysis.ipynb
│   └── model_error_analysis.ipynb
│
├── src/
│   ├── __init__.py
│   │
│   ├── ingestion/
│   │   ├── email_loader.py
│   │   ├── dataset_loader.py
│   │   └── validators.py
│   │
│   ├── parsing/
│   │   ├── email_parser.py
│   │   ├── header_parser.py
│   │   ├── html_cleaner.py
│   │   ├── url_extractor.py
│   │   └── attachment_parser.py
│   │
│   ├── features/
│   │   ├── sender_features.py
│   │   ├── url_features.py
│   │   ├── attachment_features.py
│   │   ├── text_stats.py
│   │   ├── brand_features.py
│   │   └── feature_pipeline.py
│   │
│   ├── datasets/
│   │   ├── schema.py
│   │   ├── label_mapper.py
│   │   ├── balancing.py
│   │   └── datamodule.py
│   │
│   ├── models/
│   │   ├── text_encoder.py
│   │   ├── structured_encoder.py
│   │   ├── fusion_layer.py
│   │   ├── classifier_head.py
│   │   ├── multimodal_model.py
│   │   └── losses.py
│   │
│   ├── training/
│   │   ├── train.py
│   │   ├── trainer.py
│   │   ├── evaluate.py
│   │   ├── metrics.py
│   │   ├── calibration.py
│   │   └── checkpointing.py
│   │
│   ├── inference/
│   │   ├── predictor.py
│   │   ├── postprocess.py
│   │   └── threshold_router.py
│   │
│   ├── explainability/
│   │   ├── shap_explainer.py
│   │   ├── integrated_gradients.py
│   │   ├── rule_summarizer.py
│   │   └── explanation_service.py
│   │
│   ├── feedback/
│   │   ├── feedback_ingest.py
│   │   ├── retrain_scheduler.py
│   │   └── drift_detector.py
│   │
│   ├── serving/
│   │   ├── api.py
│   │   ├── schemas.py
│   │   └── healthcheck.py
│   │
│   └── utils/
│       ├── config.py
│       ├── logger.py
│       ├── io.py
│       └── constants.py
│
├── tests/
│   ├── unit/
│   │   ├── test_parser.py
│   │   ├── test_features.py
│   │   ├── test_model.py
│   │   └── test_api.py
│   │
│   └── integration/
│       ├── test_train_pipeline.py
│       └── test_inference_pipeline.py
│
├── artifacts/
│   ├── tokenizer/
│   ├── thresholds/
│   └── reports/
│
├── checkpoints/
│   ├── baseline/
│   └── production/
│
└── scripts/
    ├── setup_env.sh
    ├── run_training.sh
    ├── run_inference.sh
    └── start_api.sh
```

---

## Key Module Responsibilities

### `src/features/`

Deterministic structured feature extraction:

- `sender_features.py` — display/From mismatch, reply-to mismatch, free-email detection
- `url_features.py` — URL count, TLD risk, entropy, typosquatting, IP literal, shortener detection
- `attachment_features.py` — attachment presence, type classification, macro detection
- `text_stats.py` — uppercase ratio, punctuation density, link density, length features
- `brand_features.py` — known brand mention detection, sender-brand mismatch
- `feature_pipeline.py` — orchestrates all feature extractors into a single feature vector

### `src/models/`

The hybrid multimodal architecture:

- `text_encoder.py` — fine-tuned RoBERTa over subject + body
- `structured_encoder.py` — MLP over deterministic structured features
- `fusion_layer.py` — concatenation and fusion of both encoder outputs
- `classifier_head.py` — binary classification head (Spam / Phishing)
- `multimodal_model.py` — full model combining all components

### `src/inference/`

- `predictor.py` — runs model inference and temperature scaling
- `threshold_router.py` — computes trust score and applies routing logic (auto-classify / Analyst Review)
- `postprocess.py` — formats final output schema

### `src/explainability/`

- `shap_explainer.py` — SHAP on structured feature MLP (inline, Tier 1)
- `integrated_gradients.py` — IG on transformer encoder (async, Tier 2)
- `rule_summarizer.py` — maps feature contributions to phrase-level sentence templates
- `explanation_service.py` — orchestrates both tiers

### `src/serving/`

- `api.py` — FastAPI REST endpoint
- `schemas.py` — Pydantic request/response schemas

### `data/processed/sampling_manifest.parquet`

Records source, era bucket, attack subtype, label, augmented flag, and split assignment for every training sample. Versioned alongside model checkpoints for full reproducibility.
