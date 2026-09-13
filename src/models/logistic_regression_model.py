"""
logistic_regression_model.py — Logistic Regression baseline definition.

Architecture used in Phase 1. Not in production — LightGBM (Phase 2b) is
the production model. Kept here for reference and reproducibility.
No inference adapter: this model is not loaded at runtime.
"""
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler

from src.models.base import STRUCTURED_COLS  # noqa: F401 — re-exported for training scripts


# ---------------------------------------------------------------------------
# Hyperparameters (Phase 1)
# ---------------------------------------------------------------------------

LR_PARAMS = {
    "C":            1.0,
    "max_iter":     1000,
    "solver":       "saga",
    "class_weight": None,   # dataset is balanced; no weighting needed
    "random_state": 42,
    "n_jobs":       -1,
}

TFIDF_PARAMS = {
    "max_features":  50_000,
    "sublinear_tf":  True,
    "ngram_range":   (1, 2),
    "min_df":        2,
    "strip_accents": "unicode",
}

# Zero-variance columns dropped before fitting
DROP_COLS = ["executable_detected", "macro_detected"]


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def build_model() -> LogisticRegression:
    return LogisticRegression(**LR_PARAMS)


def build_tfidf() -> TfidfVectorizer:
    return TfidfVectorizer(**TFIDF_PARAMS)


def build_scaler() -> StandardScaler:
    """LR requires scaled structured features; LightGBM does not."""
    return StandardScaler()
