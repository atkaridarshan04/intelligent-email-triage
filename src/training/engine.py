"""
engine.py — Core training and retraining pipeline with real-time SSE progress streaming.

Supports:
  1. Cold-Start Training from Scratch on Barclays corporate datasets.
  2. Incremental Retraining with human-in-the-loop analyst feedback.
  3. Fast Platt Scaling Recalibration.
"""
import json
import os
import pickle
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.sparse import csr_matrix, hstack
from scipy.special import expit
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from src.feedback.store import FeedbackStore
from src.models.base import STRUCTURED_COLS

DATA_DIR_DEFAULT = ROOT / "data" / "model_ready"
BARCLAYS_DATA_DIR = ROOT / "data" / "barclays_data"
CHECKPOINTS_DIR = ROOT / "checkpoints"
PROD_DIR = CHECKPOINTS_DIR / "production"
LABEL_MAP = {"spam": 0, "phishing": 1}

LGBM_PARAMS = {
    "objective": "binary",
    "metric": ["binary_logloss", "auc"],
    "learning_rate": 0.05,
    "num_leaves": 63,
    "min_child_samples": 20,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "lambda_l1": 0.1,
    "lambda_l2": 0.1,
    "verbose": -1,
    "seed": 42,
}


def load_dataset_file(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    if path.suffix == ".jsonl":
        with open(path, "r", encoding="utf-8") as f:
            return pd.DataFrame([json.loads(line) for line in f if line.strip()])
    elif path.suffix == ".csv":
        return pd.read_csv(path)
    elif path.suffix == ".parquet":
        return pd.read_parquet(path)
    else:
        # Try JSONL by default
        with open(path, "r", encoding="utf-8") as f:
            return pd.DataFrame([json.loads(line) for line in f if line.strip()])


def get_text_column(df: pd.DataFrame) -> list[str]:
    subj = df["subject"].fillna("").astype(str)
    body = df["body_text"].fillna("").astype(str)
    return (subj + " [SEP] " + body).tolist()


def ensure_structured_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all 19 structured features exist in the dataframe, defaulting missing to 0.0."""
    for col in STRUCTURED_COLS:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = df[col].fillna(0.0).astype(float)
    return df


def build_sparse_matrix(df: pd.DataFrame, tfidf: TfidfVectorizer, fit: bool = False):
    texts = get_text_column(df)
    if fit:
        X_text = tfidf.fit_transform(texts)
    else:
        X_text = tfidf.transform(texts)
    df_struct = ensure_structured_cols(df)
    X_struct = df_struct[STRUCTURED_COLS].values
    return hstack([X_text, csr_matrix(X_struct)])


def fit_platt(raw_proba: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    def loss(params):
        a, b = params
        p = np.clip(expit(a * raw_proba + b), 1e-7, 1 - 1e-7)
        return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

    result = minimize(loss, x0=[1.0, 0.0], method="L-BFGS-B")
    return float(result.x[0]), float(result.x[1])


def get_available_datasets() -> list[dict]:
    """Inspect data directories and return metadata on available datasets."""
    results = []
    candidates = [
        ("barclays_corporate", BARCLAYS_DATA_DIR, "Barclays Proprietary Corporate Data"),
        ("model_ready_baseline", DATA_DIR_DEFAULT, "Baseline Triage Dataset (Cleaned)"),
    ]

    for key, path, label in candidates:
        if not path.exists():
            results.append({
                "key": key, "label": label, "path": str(path),
                "is_available": False, "train_count": 0, "val_count": 0, "test_count": 0,
            })
            continue

        train_p = path / "train.jsonl"
        val_p = path / "val.jsonl"
        test_p = path / "test.jsonl"

        has_all = train_p.exists() and val_p.exists() and test_p.exists()
        train_count = 0
        if train_p.exists():
            try:
                with open(train_p, "rb") as f:
                    train_count = sum(1 for _ in f)
            except Exception:
                pass

        results.append({
            "key": key,
            "label": label,
            "path": str(path),
            "is_available": has_all,
            "train_count": train_count,
            "has_train": train_p.exists(),
            "has_val": val_p.exists(),
            "has_test": test_p.exists(),
        })

    return results


def stream_training_pipeline(
    mode: str = "scratch",
    data_dir_path: Optional[str] = None,
    version_tag: Optional[str] = None,
    auto_promote: bool = True,
) -> Generator[dict, None, None]:
    """
    Executes training/retraining and yields real-time progress events.
    Modes:
      - 'scratch': Cold-start training on custom/Barclays data from ground up.
      - 'full': Continuous retraining merging feedback into training corpus.
      - 'calibrate': Fast Platt scaling recalibration on validation set.
    """
    def send(progress: int, stage: str, log: str, status: str = "running", **extra):
        return {
            "progress": progress,
            "stage": stage,
            "log": log,
            "status": status,
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            **extra,
        }

    yield send(5, "Initialization", f"Initializing {mode.upper()} training pipeline engine...")
    time.sleep(0.2)

    # 1. Resolve Data Directory
    if data_dir_path:
        data_dir = Path(data_dir_path)
    elif mode == "scratch" and (BARCLAYS_DATA_DIR / "train.jsonl").exists():
        data_dir = BARCLAYS_DATA_DIR
    else:
        data_dir = DATA_DIR_DEFAULT

    yield send(10, "Data Ingestion", f"Target dataset directory: {data_dir}")

    # Mode: Fast Calibrate
    if mode == "calibrate":
        yield send(30, "Validation Loading", "Loading validation set for Platt scaling recalibration...")
        val_path = data_dir / "val.jsonl"
        val = load_dataset_file(val_path)
        y_val = val["label"].map(LABEL_MAP).values

        model_path = PROD_DIR / "lgbm.txt"
        tfidf_path = PROD_DIR / "tfidf.pkl"
        if not model_path.exists() or not tfidf_path.exists():
            yield send(100, "Error", "Production artifacts missing. Train baseline model first.", status="failed")
            return

        yield send(50, "Inference Margin", "Computing raw model decision margins on validation split...")
        model = lgb.Booster(model_file=str(model_path))
        with open(tfidf_path, "rb") as f:
            tfidf = pickle.load(f)

        X_val = build_sparse_matrix(val, tfidf, fit=False)
        raw_val = model.predict(X_val)

        yield send(75, "Platt Optimization", "Optimizing logistic sigmoid scaling parameters (a, b)...")
        a, b = fit_platt(raw_val, y_val)

        (PROD_DIR / "calibration.json").write_text(json.dumps({"a": a, "b": b}, indent=2))
        yield send(
            100, "Completed",
            f"✓ Platt recalibration complete! Fitted parameters: a={a:.4f}, b={b:.4f}",
            status="completed",
            metrics={"platt_a": a, "platt_b": b},
        )
        return

    # 2. Ingest Dataset Splits
    yield send(18, "Dataset Ingestion", f"Loading train, val, and test splits from {data_dir}...")
    try:
        train = load_dataset_file(data_dir / "train.jsonl")
        val = load_dataset_file(data_dir / "val.jsonl")
        test = load_dataset_file(data_dir / "test.jsonl")
    except Exception as e:
        yield send(100, "Ingestion Error", f"Failed loading dataset files: {e}", status="failed")
        return

    train = train.loc[train["label"].isin(LABEL_MAP)].copy()
    val = val.loc[val["label"].isin(LABEL_MAP)].copy()
    test = test.loc[test["label"].isin(LABEL_MAP)].copy()

    yield send(
        25, "Dataset Validation",
        f"Ingested {len(train):,} training, {len(val):,} validation, and {len(test):,} test samples."
    )

    # Ingest analyst feedback if full retraining mode
    fb_count = 0
    if mode == "full":
        yield send(30, "Feedback Ingestion", "Scanning SQLite feedback database for analyst reviews...")
        store = FeedbackStore()
        feedback = store.get_labeled_feedback()
        if feedback:
            fb_df = pd.DataFrame(feedback)
            valid_fb = fb_df[fb_df["features"].apply(lambda f: isinstance(f, dict) and len(f) > 0)]
            if not valid_fb.empty:
                for col in STRUCTURED_COLS:
                    valid_fb[col] = valid_fb["features"].apply(lambda f: f.get(col, 0.0))
                train = pd.concat([train, valid_fb[train.columns.intersection(valid_fb.columns)]], ignore_index=True)
                fb_count = len(valid_fb)
                yield send(34, "Feedback Merged", f"Merged {fb_count} verified SOC analyst feedback samples into training pool.")
        else:
            yield send(34, "Feedback Scanned", "No new feedback samples in database. Proceeding with base data.")

    y_train = train["label"].map(LABEL_MAP).values
    y_val = val["label"].map(LABEL_MAP).values
    y_test = test["label"].map(LABEL_MAP).values

    # 3. Fit TF-IDF Vectorizer & Assemble Features
    yield send(
        40, "Feature Engineering",
        f"Fitting TF-IDF vocabulary on {len(train):,} emails (30,000 max features, n-gram (1,2), sublinear TF)..."
    )
    tfidf = TfidfVectorizer(
        max_features=30_000,
        sublinear_tf=True,
        ngram_range=(1, 2),
        min_df=2,
        strip_accents="unicode",
    )

    X_train = build_sparse_matrix(train, tfidf, fit=True)
    yield send(48, "Vectorization", f"Built X_train sparse matrix: {X_train.shape[0]:,} samples × {X_train.shape[1]:,} features.")

    X_val = build_sparse_matrix(val, tfidf, fit=False)
    X_test = build_sparse_matrix(test, tfidf, fit=False)

    # 4. LightGBM Booster Training
    yield send(55, "LightGBM Training", "Training LightGBM gradient boosted decision trees (max 1000 rounds, early stopping=50)...")

    ds_train = lgb.Dataset(X_train, label=y_train)
    ds_val = lgb.Dataset(X_val, label=y_val, reference=ds_train)

    evals_result = {}
    callbacks = [
        lgb.early_stopping(stopping_rounds=50, verbose=False),
        lgb.record_evaluation(evals_result),
    ]

    model = lgb.train(
        LGBM_PARAMS,
        ds_train,
        num_boost_round=1000,
        valid_sets=[ds_train, ds_val],
        valid_names=["train", "val"],
        callbacks=callbacks,
    )

    best_round = model.best_iteration or 100
    val_auc = evals_result.get("val", {}).get("auc", [0.0])[-1]
    yield send(
        70, "Training Converged",
        f"LightGBM converged at round {best_round}. Best validation AUC: {val_auc:.4f}."
    )

    # 5. Platt Calibration
    yield send(75, "Probability Calibration", "Fitting Platt scaling parameters on validation split...")
    raw_val = model.predict(X_val)
    platt_a, platt_b = fit_platt(raw_val, y_val)
    yield send(80, "Calibration Fitted", f"Calibrated Platt scaling parameters: a={platt_a:.4f}, b={platt_b:.4f}.")

    # 6. Evaluation on Holdout Test Set
    yield send(85, "Holdout Evaluation", f"Evaluating calibrated model on {len(test):,} holdout test samples...")
    raw_test = model.predict(X_test)
    p_test = expit(platt_a * raw_test + platt_b)
    y_pred = (p_test >= 0.5).astype(int)

    phishing_recall = float(recall_score(y_test, y_pred))
    accuracy = float(accuracy_score(y_test, y_pred))
    precision = float(precision_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))

    yield send(
        90, "Evaluation Metrics",
        f"Test Results — Phishing Recall: {phishing_recall * 100:.2f}%, Accuracy: {accuracy * 100:.2f}%, F1: {f1 * 100:.2f}%."
    )

    # Quality Gate Check for Retraining
    current_recall = 0.0
    if (PROD_DIR / "manifest.json").exists():
        try:
            prod_manifest = json.loads((PROD_DIR / "manifest.json").read_text())
            current_recall = prod_manifest.get("metrics", {}).get("phishing_recall", 0.0)
        except Exception:
            current_recall = 0.0

    if mode == "full" and phishing_recall < current_recall:
        err_msg = f"QUALITY GATE REJECTED: New recall ({phishing_recall * 100:.2f}%) < Production baseline ({current_recall * 100:.2f}%). Reverting."
        yield send(100, "Gate Rejected", err_msg, status="failed", metrics={"phishing_recall": phishing_recall, "production_recall": current_recall})
        return

    # 7. Save Checkpoint Artifacts
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    if not version_tag:
        version = f"barclays-v{date_str}" if mode == "scratch" else f"lightgbm-v{date_str}"
    else:
        version = version_tag

    out_dir = CHECKPOINTS_DIR / version
    out_dir.mkdir(parents=True, exist_ok=True)

    model.save_model(str(out_dir / "lgbm.txt"))
    with open(out_dir / "tfidf.pkl", "wb") as f:
        pickle.dump(tfidf, f)
    (out_dir / "calibration.json").write_text(json.dumps({"a": platt_a, "b": platt_b}, indent=2))

    manifest = {
        "version": version,
        "model_type": "lightgbm",
        "training_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "dataset_source": str(data_dir.name),
        "metrics": {
            "phishing_recall": phishing_recall,
            "accuracy": accuracy,
            "precision": precision,
            "f1": f1,
        },
        "artifacts": {
            "model": "lgbm.txt",
            "vectorizer": "tfidf.pkl",
            "calibration": "calibration.json",
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    yield send(95, "Artifacts Saved", f"Serialized model artifacts to checkpoints/{version}.")

    # 8. Auto-Promotion & Hot-Reload
    if auto_promote:
        yield send(97, "Production Promotion", f"Promoting {version} to checkpoints/production...")
        try:
            from scripts.promote_model import promote_checkpoint
            res = promote_checkpoint(version)
            if res["success"]:
                from src.serving.api import reload_predictor
                reload_predictor()
                yield send(99, "Hot-Reloaded", f"Successfully hot-reloaded active predictor with {version} in memory (Zero Downtime)!")
        except Exception as e:
            yield send(98, "Promotion Warning", f"Saved checkpoint but hot-reload noted: {e}")

    yield send(
        100, "Pipeline Succeeded",
        f"✓ Training pipeline complete! Model {version} is fully active with {phishing_recall * 100:.2f}% Phishing Recall.",
        status="completed",
        version=version,
        metrics={
            "phishing_recall": round(phishing_recall * 100, 2),
            "accuracy": round(accuracy * 100, 2),
            "precision": round(precision * 100, 2),
            "f1": round(f1 * 100, 2),
        },
    )
