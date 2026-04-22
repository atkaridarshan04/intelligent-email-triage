# Production-Grade Folder Structure

## Adaptive Email Intelligence Model (Spam / Junk / Phishing)

```text
email-intelligence-platform/
│
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── Makefile
│
├── configs/
│   ├── base.yaml
│   ├── train.yaml
│   ├── inference.yaml
│   ├── logging.yaml
│   └── thresholds.yaml
│
├── data/
│   ├── raw/
│   │   ├── enron/
│   │   ├── spamassassin/
│   │   ├── phishing/
│   │   └── urls/
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
│   │   └── feature_store/
│   │
│   └── feedback/
│       ├── analyst_labels/
│       └── false_positive_cases/
│
├── notebooks/
│   ├── eda.ipynb
│   ├── labeling_strategy.ipynb
│   ├── drift_analysis.ipynb
│   └── model_error_analysis.ipynb
│
├── src/
│   ├── __init__.py
│   │
│   ├── ingestion/
│   │   ├── email_loader.py
│   │   ├── dataset_loader.py
│   │   ├── stream_consumer.py
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
│   │   ├── text_features.py
│   │   ├── metadata_features.py
│   │   ├── behavioral_features.py
│   │   ├── url_features.py
│   │   ├── encoders.py
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
│   │   ├── metadata_encoder.py
│   │   ├── behavior_encoder.py
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
│   │   ├── threshold_router.py
│   │   └── batch_inference.py
│   │
│   ├── explainability/
│   │   ├── shap_explainer.py
│   │   ├── attention_scores.py
│   │   ├── rationale_generator.py
│   │   └── explanation_service.py
│   │
│   ├── online_learning/
│   │   ├── feedback_ingest.py
│   │   ├── drift_detector.py
│   │   ├── incremental_update.py
│   │   ├── retrain_scheduler.py
│   │   └── active_learning.py
│   │
│   ├── serving/
│   │   ├── api.py
│   │   ├── schemas.py
│   │   ├── auth.py
│   │   ├── middleware.py
│   │   └── healthcheck.py
│   │
│   ├── monitoring/
│   │   ├── model_metrics.py
│   │   ├── latency_metrics.py
│   │   ├── drift_metrics.py
│   │   ├── logging_utils.py
│   │   └── alerts.py
│   │
│   ├── utils/
│   │   ├── config.py
│   │   ├── logger.py
│   │   ├── seed.py
│   │   ├── io.py
│   │   └── constants.py
│   │
│   └── pipelines/
│       ├── train_pipeline.py
│       ├── inference_pipeline.py
│       ├── feedback_pipeline.py
│       └── deployment_pipeline.py
│
├── tests/
│   ├── unit/
│   │   ├── test_parser.py
│   │   ├── test_features.py
│   │   ├── test_model.py
│   │   └── test_api.py
│   │
│   ├── integration/
│   │   ├── test_train_pipeline.py
│   │   ├── test_inference_pipeline.py
│   │   └── test_feedback_loop.py
│   │
│   └── performance/
│       ├── load_test_api.py
│       └── latency_benchmark.py
│
├── artifacts/
│   ├── tokenizer/
│   ├── label_encoders/
│   ├── thresholds/
│   └── reports/
│
├── checkpoints/
│   ├── baseline/
│   ├── staging/
│   └── production/
│
├── logs/
│   ├── training/
│   ├── inference/
│   └── drift/
│
└── scripts/
    ├── setup_env.sh
    ├── run_training.sh
    ├── run_inference.sh
    ├── start_api.sh
    ├── retrain_weekly.sh
    └── backup_models.sh
```

# Folder Purpose Summary

## configs/

All tunable parameters:

* learning rate
* thresholds
* model names
* batch sizes
* routing logic

---

## data/

Raw + processed datasets + analyst feedback loop.

---

## src/models/

Contains your unified multimodal architecture:

* text encoder
* metadata encoder
* behavior encoder
* fusion classifier

---

## src/training/

All training logic.

---

## src/inference/

Real-time prediction pipeline.

---

## src/explainability/

Reason generation for SOC analysts.

---

## src/online_learning/

Drift detection + continual updates.

---

## src/serving/

REST API deployment.

---

## tests/

Production-grade testing.

---

# Most Important Core Files

## Main Model

```text
src/models/multimodal_model.py
```

## Train Model

```text
src/training/train.py
```

## Predict API

```text
src/serving/api.py
```

## Online Learning

```text
src/online_learning/retrain_scheduler.py
```

---

# If Student/Hackathon Version Needed

Use reduced structure:

```text
src/
 ├── data.py
 ├── features.py
 ├── model.py
 ├── train.py
 ├── predict.py
 ├── api.py
```

---

# Final Recommendation

For presentation:

> We designed the repository using production ML standards with modular pipelines for ingestion, multimodal modeling, explainability, online learning, and scalable deployment.

That sounds enterprise-grade and real.

---
