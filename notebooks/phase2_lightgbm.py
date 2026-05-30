# =============================================================================
# PHASE 2 — LIGHTGBM ENTERPRISE CANDIDATE
# Intelligent Email Triage — Spam vs Phishing
#
# Kaggle usage: paste each cell block into a separate notebook cell.
# Run AFTER phase1_baseline.py — reuses the same data loading pattern.
# =============================================================================


# ── CELL 1: Install & imports ─────────────────────────────────────────────────
# !pip install lightgbm shap --quiet  # both available on Kaggle by default

import json
import numpy as np
import pandas as pd
from pathlib import Path
import lightgbm as lgb
import shap
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, average_precision_score,
    brier_score_loss, recall_score, ConfusionMatrixDisplay
)
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")


# ── CELL 2: Load data ─────────────────────────────────────────────────────────
DATA_DIR = Path("/kaggle/input/email-triage-model-ready")  # <-- update if needed

def load_jsonl(path):
    with open(path) as f:
        return pd.DataFrame([json.loads(l) for l in f if l.strip()])

train = load_jsonl(DATA_DIR / "train.jsonl")
val   = load_jsonl(DATA_DIR / "val.jsonl")
test  = load_jsonl(DATA_DIR / "test.jsonl")

LABEL_MAP = {"spam": 0, "phishing": 1}
y_train = train["label"].map(LABEL_MAP).values
y_val   = val["label"].map(LABEL_MAP).values
y_test  = test["label"].map(LABEL_MAP).values

print(f"Train: {len(train)}  Val: {len(val)}  Test: {len(test)}")


# ── CELL 3: Feature preparation ───────────────────────────────────────────────
# Zero-variance in this dataset — drop before fitting
DROP_COLS = ["executable_detected", "macro_detected"]

STRUCTURED_COLS = [
    "display_from_mismatch", "reply_to_mismatch", "free_email_sender",
    "url_count", "domain_count", "shortened_url_present", "suspicious_tld_present",
    "ip_literal_url", "url_entropy", "typosquatting_detected",
    "has_attachment",
    "subject_length", "body_length", "uppercase_ratio", "digit_ratio",
    "punctuation_density", "link_density",
    "brand_mention", "sender_brand_mismatch",
]

def get_text(df):
    subj = df["subject"].fillna("").astype(str)
    body = df["body_text"].fillna("").astype(str)
    return (subj + " [SEP] " + body).tolist()

# TF-IDF — LightGBM handles sparse input natively
tfidf = TfidfVectorizer(
    max_features=30_000,
    sublinear_tf=True,
    ngram_range=(1, 2),
    min_df=2,
    strip_accents="unicode",
)
X_text_train = tfidf.fit_transform(get_text(train))
X_text_val   = tfidf.transform(get_text(val))
X_text_test  = tfidf.transform(get_text(test))

# Structured features — LightGBM does NOT need scaling
X_struct_train = train[STRUCTURED_COLS].astype(float).values
X_struct_val   = val[STRUCTURED_COLS].astype(float).values
X_struct_test  = test[STRUCTURED_COLS].astype(float).values

from scipy.sparse import hstack, csr_matrix
X_train = hstack([X_text_train, csr_matrix(X_struct_train)])
X_val   = hstack([X_text_val,   csr_matrix(X_struct_val)])
X_test  = hstack([X_text_test,  csr_matrix(X_struct_test)])

feature_names = tfidf.get_feature_names_out().tolist() + STRUCTURED_COLS

print(f"Feature matrix — Train: {X_train.shape}")


# ── CELL 4: Train LightGBM ────────────────────────────────────────────────────
lgb_train = lgb.Dataset(X_train, label=y_train, feature_name=feature_names)
lgb_val   = lgb.Dataset(X_val,   label=y_val,   reference=lgb_train)

params = {
    "objective":       "binary",
    "metric":          ["binary_logloss", "auc"],
    "learning_rate":   0.05,
    "num_leaves":      63,
    "min_child_samples": 20,
    "feature_fraction":  0.8,
    "bagging_fraction":  0.8,
    "bagging_freq":      5,
    "lambda_l1":         0.1,
    "lambda_l2":         0.1,
    "verbose":          -1,
    "seed":             42,
}

callbacks = [
    lgb.early_stopping(stopping_rounds=50, verbose=True),
    lgb.log_evaluation(period=100),
]

model = lgb.train(
    params,
    lgb_train,
    num_boost_round=1000,
    valid_sets=[lgb_val],
    callbacks=callbacks,
)

print(f"\nBest iteration: {model.best_iteration}")


# ── CELL 5: Calibrate on validation set ──────────────────────────────────────
# Use Platt scaling directly on raw LightGBM probabilities (no sklearn wrapper needed)
from scipy.special import expit
from scipy.optimize import minimize

raw_val_proba = model.predict(X_val)   # raw sigmoid outputs from LightGBM

# Fit Platt scaling: find a, b such that calibrated = sigmoid(a * raw + b)
def platt_loss(params, raw, y):
    a, b = params
    p = expit(a * raw + b)
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

result = minimize(platt_loss, x0=[1.0, 0.0], args=(raw_val_proba, y_val), method="L-BFGS-B")
platt_a, platt_b = result.x

def calibrated_predict_proba(X):
    raw = model.predict(X)
    p = expit(platt_a * raw + platt_b)
    return np.column_stack([1 - p, p])

# Unified interface matching the rest of the notebook
class CalibratedModel:
    def predict_proba(self, X):
        return calibrated_predict_proba(X)
    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)

calibrated = CalibratedModel()
print(f"Platt scaling fit: a={platt_a:.4f}, b={platt_b:.4f}")


# ── CELL 6: Evaluate ──────────────────────────────────────────────────────────
def evaluate(model, X, y_true, split_name):
    y_pred  = model.predict(X)
    y_proba = model.predict_proba(X)[:, 1]

    print(f"\n{'='*50}")
    print(f"  {split_name}")
    print(f"{'='*50}")
    print(classification_report(y_true, y_pred, target_names=["spam", "phishing"], digits=4))
    print(f"ROC-AUC:   {roc_auc_score(y_true, y_proba):.4f}")
    print(f"PR-AUC:    {average_precision_score(y_true, y_proba):.4f}")
    print(f"Brier:     {brier_score_loss(y_true, y_proba):.4f}")

    cm = confusion_matrix(y_true, y_pred)
    ConfusionMatrixDisplay(cm, display_labels=["spam", "phishing"]).plot(cmap="Blues")
    plt.title(f"Confusion Matrix — {split_name}")
    plt.tight_layout(); plt.show()

    return y_proba

val_proba  = evaluate(calibrated, X_val,  y_val,  "Validation Set")
test_proba = evaluate(calibrated, X_test, y_test, "Test Set (held-out)")


# ── CELL 7: Confidence routing simulation ────────────────────────────────────
def trust_score(proba_phishing, w1=0.6, w2=0.4):
    max_prob = np.maximum(proba_phishing, 1 - proba_phishing)
    margin   = np.abs(2 * proba_phishing - 1)
    return (w1 * max_prob + w2 * margin) * 100

def route(trust):
    if trust > 90:  return "auto_classify"
    if trust > 75:  return "auto_classify_monitor"
    if trust > 55:  return "analyst_review"
    return "priority_analyst_review"

test_trust  = trust_score(test_proba)
test_routes = pd.Series([route(t) for t in test_trust])

print("\n=== ROUTING DISTRIBUTION (Test Set) ===")
print(test_routes.value_counts().to_dict())

auto_mask = test_trust > 75
print(f"\nAuto-classified: {auto_mask.sum()} / {len(y_test)} ({auto_mask.mean()*100:.1f}%)")
if auto_mask.sum() > 0:
    print(f"Phishing recall (auto only): {recall_score(y_test[auto_mask], (test_proba[auto_mask] >= 0.5).astype(int)):.4f}")

# Security override check: phishing_prob > 0.70 AND any high-risk signal
high_risk_signals = ["typosquatting_detected", "ip_literal_url", "reply_to_mismatch",
                     "suspicious_tld_present", "sender_brand_mismatch"]
test_high_risk = test[high_risk_signals].any(axis=1).values
override_mask  = (test_proba > 0.70) & test_high_risk
print(f"\nSecurity override triggered: {override_mask.sum()} emails")


# ── CELL 8: Calibration curve + ECE ──────────────────────────────────────────
prob_true, prob_pred = calibration_curve(y_test, test_proba, n_bins=10)
plt.figure(figsize=(6, 5))
plt.plot(prob_pred, prob_true, "s-", label="LightGBM (calibrated)")
plt.plot([0, 1], [0, 1], "k--", label="Perfect")
plt.xlabel("Mean predicted probability"); plt.ylabel("Fraction of positives")
plt.title("Calibration Curve — Test Set"); plt.legend()
plt.tight_layout(); plt.show()

bin_edges = np.linspace(0, 1, 11)
ece = sum(
    ((test_proba >= bin_edges[i]) & (test_proba < bin_edges[i+1])).mean() *
    abs(
        (y_test[(test_proba >= bin_edges[i]) & (test_proba < bin_edges[i+1])] ==
         (test_proba[(test_proba >= bin_edges[i]) & (test_proba < bin_edges[i+1])] >= 0.5).astype(int)).mean()
        - test_proba[(test_proba >= bin_edges[i]) & (test_proba < bin_edges[i+1])].mean()
    )
    for i in range(len(bin_edges) - 1)
    if ((test_proba >= bin_edges[i]) & (test_proba < bin_edges[i+1])).sum() > 0
)
print(f"ECE: {ece:.4f}  (target < 0.05)")


# ── CELL 9: SHAP explainability (structured features only) ───────────────────
# SHAP on full sparse matrix is slow — explain structured features only
X_struct_test_df = pd.DataFrame(X_struct_test, columns=STRUCTURED_COLS)

# Re-train a structured-only LightGBM for SHAP (fast, interpretable)
lgb_struct_train = lgb.Dataset(X_struct_train, label=y_train)
lgb_struct_val   = lgb.Dataset(X_struct_val,   label=y_val, reference=lgb_struct_train)

struct_model = lgb.train(
    {**params, "num_leaves": 31},
    lgb_struct_train,
    num_boost_round=300,
    valid_sets=[lgb_struct_val],
    callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],
)

explainer   = shap.TreeExplainer(struct_model)
shap_values = explainer.shap_values(X_struct_test)

plt.figure()
shap.summary_plot(shap_values, X_struct_test_df, plot_type="bar", show=False)
plt.title("SHAP Feature Importance — Structured Features")
plt.tight_layout(); plt.show()

plt.figure()
shap.summary_plot(shap_values, X_struct_test_df, show=False)
plt.title("SHAP Beeswarm — Structured Features")
plt.tight_layout(); plt.show()


# ── CELL 10: Save model artifacts ────────────────────────────────────────────
import pickle, os

OUT_DIR = Path("/kaggle/working")
model.save_model(str(OUT_DIR / "lgbm_phase2.txt"))

with open(OUT_DIR / "tfidf_phase2.pkl", "wb") as f:
    pickle.dump(tfidf, f)

with open(OUT_DIR / "calibrated_phase2.pkl", "wb") as f:
    pickle.dump(calibrated, f)

print("Artifacts saved to /kaggle/working/")
