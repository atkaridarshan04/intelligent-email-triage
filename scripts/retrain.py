"""
retrain.py — Retraining pipeline for the LightGBM production model.

Modes:
  --mode calibrate  Refit Platt scaling only on current validation set.
                    Use when < 500 new labeled samples. Runtime < 2 min.

  --mode full       Merge feedback into training data, retrain LightGBM,
                    calibrate, evaluate, gate on phishing recall, save artifacts.
                    Use when >= 500 new samples or override rate breached.

Usage:
  python scripts/retrain.py --mode full
  python scripts/retrain.py --mode calibrate
"""
import argparse
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.sparse import csr_matrix, hstack
from scipy.special import expit
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import recall_score

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from src.feedback.store import FeedbackStore
from src.inference.adapter import STRUCTURED_COLS

DATA_DIR = ROOT / "data" / "model_ready"
PROD_DIR = ROOT / "checkpoints" / "production"

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_jsonl(path: Path) -> pd.DataFrame:
    with open(path) as f:
        return pd.DataFrame([json.loads(l) for l in f if l.strip()])


def get_text(df: pd.DataFrame) -> list[str]:
    return (df["subject"].fillna("").astype(str) + " [SEP] " + df["body_text"].fillna("").astype(str)).tolist()


def fit_platt(raw_proba: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    def loss(params):
        a, b = params
        p = np.clip(expit(a * raw_proba + b), 1e-7, 1 - 1e-7)
        return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

    result = minimize(loss, x0=[1.0, 0.0], method="L-BFGS-B")
    return float(result.x[0]), float(result.x[1])


def build_features(df: pd.DataFrame, tfidf: TfidfVectorizer, fit: bool = False):
    if fit:
        X_text = tfidf.fit_transform(get_text(df))
    else:
        X_text = tfidf.transform(get_text(df))
    X_struct = df[STRUCTURED_COLS].fillna(0).astype(float).values
    return hstack([X_text, csr_matrix(X_struct)])


def load_current_recall() -> float:
    manifest = json.loads((PROD_DIR / "manifest.json").read_text())
    return manifest.get("metrics", {}).get("phishing_recall", 0.0)


def save_artifacts(
    model: lgb.Booster,
    tfidf: TfidfVectorizer,
    platt_a: float,
    platt_b: float,
    metrics: dict,
    version: str,
) -> Path:
    out_dir = ROOT / "checkpoints" / version
    out_dir.mkdir(parents=True, exist_ok=True)

    model.save_model(str(out_dir / "lgbm.txt"))
    with open(out_dir / "tfidf.pkl", "wb") as f:
        pickle.dump(tfidf, f)
    (out_dir / "calibration.json").write_text(json.dumps({"a": platt_a, "b": platt_b}, indent=2))

    manifest = json.loads((PROD_DIR / "manifest.json").read_text())
    manifest["version"] = version
    manifest["training_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    manifest["metrics"] = metrics
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    return out_dir


# ---------------------------------------------------------------------------
# Execution Engine (CLI + Programmatic)
# ---------------------------------------------------------------------------

def execute_retrain(mode: str = "full", exit_on_fail: bool = True) -> dict:
    if mode == "calibrate":
        print("Mode: calibrate — refitting Platt scaling on validation set")
        val = load_jsonl(DATA_DIR / "val.jsonl")
        y_val = val["label"].map(LABEL_MAP).values

        model = lgb.Booster(model_file=str(PROD_DIR / "lgbm.txt"))
        with open(PROD_DIR / "tfidf.pkl", "rb") as f:
            tfidf = pickle.load(f)

        X_val = build_features(val, tfidf, fit=False)
        raw = model.predict(X_val)
        a, b = fit_platt(raw, y_val)

        (PROD_DIR / "calibration.json").write_text(json.dumps({"a": a, "b": b}, indent=2))
        msg = f"Calibration updated: a={a:.4f}, b={b:.4f}"
        print(msg)
        return {
            "success": True,
            "mode": "calibrate",
            "platt_a": a,
            "platt_b": b,
            "message": msg,
        }

    print("Mode: full — loading base training data + analyst feedback")
    train = load_jsonl(DATA_DIR / "train.jsonl")
    val = load_jsonl(DATA_DIR / "val.jsonl")
    test = load_jsonl(DATA_DIR / "test.jsonl")

    # Merge feedback — analyst labels take precedence
    store = FeedbackStore()
    feedback = store.get_labeled_feedback()
    fb_count = 0
    if feedback:
        fb_df = pd.DataFrame(feedback)
        valid_fb = fb_df[fb_df["features"].apply(lambda f: isinstance(f, dict) and len(f) > 0)]
        if not valid_fb.empty:
            for col in STRUCTURED_COLS:
                valid_fb[col] = valid_fb["features"].apply(lambda f: f.get(col, 0.0))
            train = pd.concat([train, valid_fb[train.columns.intersection(valid_fb.columns)]], ignore_index=True)
            fb_count = len(valid_fb)
            print(f"Added {fb_count} analyst-labeled samples")

    y_train = train["label"].map(LABEL_MAP).dropna().values
    train = train.loc[train["label"].isin(LABEL_MAP)]
    y_val = val["label"].map(LABEL_MAP).values
    y_test = test["label"].map(LABEL_MAP).values

    tfidf = TfidfVectorizer(max_features=30_000, sublinear_tf=True, ngram_range=(1, 2), min_df=2, strip_accents="unicode")
    X_train = build_features(train, tfidf, fit=True)
    X_val = build_features(val, tfidf)
    X_test = build_features(test, tfidf)

    print(f"Training on {X_train.shape[0]} samples, {X_train.shape[1]} features")

    ds_train = lgb.Dataset(X_train, label=y_train)
    ds_val = lgb.Dataset(X_val, label=y_val, reference=ds_train)

    model = lgb.train(
        LGBM_PARAMS,
        ds_train,
        num_boost_round=1000,
        valid_sets=[ds_val],
        callbacks=[lgb.early_stopping(50, verbose=True), lgb.log_evaluation(100)],
    )

    raw_val = model.predict(X_val)
    platt_a, platt_b = fit_platt(raw_val, y_val)

    # Evaluate on test set
    raw_test = model.predict(X_test)
    p_test = expit(platt_a * raw_test + platt_b)
    y_pred = (p_test >= 0.5).astype(int)
    phishing_recall = float(recall_score(y_test, y_pred))
    accuracy = float((y_pred == y_test).mean())

    print(f"\nTest — phishing recall: {phishing_recall:.4f}  accuracy: {accuracy:.4f}")

    current_recall = load_current_recall()
    gate_passed = phishing_recall >= current_recall
    if not gate_passed:
        err_msg = f"GATE FAILED: new recall {phishing_recall:.4f} < production {current_recall:.4f}. Artifacts NOT saved."
        print(err_msg)
        if exit_on_fail:
            sys.exit(1)
        return {
            "success": False,
            "gate_passed": False,
            "phishing_recall": phishing_recall,
            "production_recall": current_recall,
            "accuracy": accuracy,
            "message": err_msg,
        }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    version = f"lightgbm-v{timestamp}"
    out_dir = save_artifacts(
        model, tfidf, platt_a, platt_b,
        metrics={"phishing_recall": phishing_recall, "accuracy": accuracy},
        version=version,
    )

    print(f"\nArtifacts saved to {out_dir}")
    print(f"To promote: python scripts/promote_model.py --version {version}")

    return {
        "success": True,
        "gate_passed": True,
        "version": version,
        "phishing_recall": phishing_recall,
        "accuracy": accuracy,
        "feedback_samples_added": fb_count,
        "artifacts_dir": str(out_dir),
        "message": f"Retrained successfully: version {version} passed recall gate ({phishing_recall:.4f} >= {current_recall:.4f}).",
    }


def run_calibrate():
    execute_retrain(mode="calibrate", exit_on_fail=True)


def run_full():
    execute_retrain(mode="full", exit_on_fail=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full", "calibrate"], default="full")
    args = parser.parse_args()

    if args.mode == "calibrate":
        run_calibrate()
    else:
        run_full()
