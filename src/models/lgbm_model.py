"""
lgbm_model.py — LightGBM model definition, calibration, and inference adapter.

Architecture used in Phase 2 / Phase 2b (production model).
Training is done on Kaggle; artifacts are exported into checkpoints/production/.

Artifact plugin: LightGBMAdapter satisfies the ModelAdapter protocol and is
loaded by Predictor when manifest.json specifies model_type="lightgbm".
"""
import json
import pickle
from pathlib import Path

import numpy as np
from scipy.sparse import hstack, csr_matrix
from scipy.special import expit, logit
from scipy.optimize import minimize, minimize_scalar

from src.models.base import ModelAdapter, ModelOutput, STRUCTURED_COLS


# ---------------------------------------------------------------------------
# Training hyperparameters (Phase 2b)
# ---------------------------------------------------------------------------

LGBM_PARAMS = {
    "objective":         "binary",
    "metric":            ["binary_logloss", "auc"],
    "learning_rate":     0.05,
    "num_leaves":        63,
    "min_child_samples": 20,
    "feature_fraction":  0.8,
    "bagging_fraction":  0.8,
    "bagging_freq":      5,
    "lambda_l1":         0.1,
    "lambda_l2":         0.1,
    "verbose":           -1,
    "seed":              42,
}

LGBM_FIT_PARAMS = {
    "num_boost_round": 1000,
    "early_stopping":  50,
}

TFIDF_PARAMS = {
    "max_features":  30_000,
    "sublinear_tf":  True,
    "ngram_range":   (1, 2),
    "min_df":        2,
    "strip_accents": "unicode",
}


# ---------------------------------------------------------------------------
# Calibration helpers
# ---------------------------------------------------------------------------

def fit_platt_scaling(raw_proba: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Fit Platt scaling parameters a, b on a held-out validation set."""
    def loss(params):
        a, b = params
        p = np.clip(expit(a * raw_proba + b), 1e-7, 1 - 1e-7)
        return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

    result = minimize(loss, x0=[1.0, 0.0], method="L-BFGS-B")
    return float(result.x[0]), float(result.x[1])


def fit_temperature_scaling(raw_proba: np.ndarray, y: np.ndarray) -> float:
    """Fit a single temperature scalar T on a held-out validation set (Phase 2b)."""
    def loss(T):
        p = np.clip(expit(logit(np.clip(raw_proba, 1e-7, 1 - 1e-7)) / T), 1e-7, 1 - 1e-7)
        return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

    return float(minimize_scalar(loss, bounds=(0.1, 10.0), method="bounded").x)


# ---------------------------------------------------------------------------
# CalibratedModel (matches class saved in calibrated_phase2.pkl)
# ---------------------------------------------------------------------------

class CalibratedModel:
    """
    Wraps a trained LightGBM booster with Platt or temperature calibration.
    platt_a / platt_b are exposed as attributes for export_artifacts.py.
    """

    def __init__(self, booster, calibration: str = "platt",
                 a: float = 1.0, b: float = 0.0, T: float = 1.0):
        self.booster     = booster
        self.calibration = calibration
        self.platt_a     = a
        self.platt_b     = b
        self.temperature = T

    def _calibrate(self, raw: np.ndarray) -> np.ndarray:
        if self.calibration == "temperature":
            return expit(logit(np.clip(raw, 1e-7, 1 - 1e-7)) / self.temperature)
        return expit(self.platt_a * raw + self.platt_b)

    def predict_proba(self, X) -> np.ndarray:
        p = self._calibrate(self.booster.predict(X))
        return np.column_stack([1 - p, p])

    def predict(self, X) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


# ---------------------------------------------------------------------------
# Inference adapter (artifact plugin)
# ---------------------------------------------------------------------------

class LightGBMAdapter:
    """
    Loads trained artifacts from a checkpoint directory and satisfies
    the ModelAdapter protocol. Registered in Predictor for model_type="lightgbm".
    """

    def __init__(self, checkpoint_dir: Path):
        import lightgbm as lgb
        import shap

        manifest   = json.loads((checkpoint_dir / "manifest.json").read_text())
        artifacts  = manifest.get("artifacts", {})
        self._version = manifest["version"]

        self._model = lgb.Booster(model_file=str(checkpoint_dir / artifacts.get("model", "lgbm.txt")))

        with open(checkpoint_dir / artifacts.get("vectorizer", "tfidf.pkl"), "rb") as f:
            self._tfidf = pickle.load(f)

        cal = json.loads((checkpoint_dir / artifacts.get("calibration", "calibration.json")).read_text())
        self._platt_a = cal["a"]
        self._platt_b = cal["b"]

        self._explainer = shap.TreeExplainer(self._model)

    def predict(self, text: str, features: dict[str, float]) -> ModelOutput:
        X_text     = self._tfidf.transform([text])
        struct_row = np.array([[features.get(c, 0.0) for c in STRUCTURED_COLS]], dtype=float)
        X          = hstack([X_text, csr_matrix(struct_row)])

        raw        = self._model.predict(X)[0]
        p_phishing = float(expit(self._platt_a * raw + self._platt_b))

        shap_vals = self._explainer.shap_values(struct_row)
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1]
        attributions = {col: float(shap_vals[0][i]) for i, col in enumerate(STRUCTURED_COLS)}

        return ModelOutput(spam_prob=1.0 - p_phishing, phishing_prob=p_phishing,
                           feature_attributions=attributions)

    def version(self) -> str:
        return self._version

    def model_type(self) -> str:
        return "lightgbm"
