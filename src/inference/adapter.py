"""
adapter.py — ModelAdapter Protocol and LightGBMAdapter.

LightGBMAdapter loads:
  - checkpoints/production/lgbm.txt         (LightGBM model)
  - checkpoints/production/tfidf.pkl        (TF-IDF vectorizer)
  - checkpoints/production/calibration.json (Platt scaling a, b)
  - checkpoints/production/manifest.json    (version metadata)
"""
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from scipy.sparse import hstack, csr_matrix
from scipy.special import expit


# ---------------------------------------------------------------------------
# Protocol — the only interface the rest of the system depends on
# ---------------------------------------------------------------------------

@dataclass
class ModelOutput:
    spam_prob: float
    phishing_prob: float
    feature_attributions: dict[str, float]  # feature_name -> SHAP value


class ModelAdapter(Protocol):
    def predict(self, text: str, features: dict[str, float]) -> ModelOutput: ...
    def version(self) -> str: ...
    def model_type(self) -> str: ...


# ---------------------------------------------------------------------------
# Structured feature columns — must match training order exactly
# ---------------------------------------------------------------------------

STRUCTURED_COLS = [
    "display_from_mismatch", "reply_to_mismatch", "free_email_sender",
    "url_count", "domain_count", "shortened_url_present", "suspicious_tld_present",
    "ip_literal_url", "url_entropy", "typosquatting_detected",
    "has_attachment",
    "subject_length", "body_length", "uppercase_ratio", "digit_ratio",
    "punctuation_density", "link_density",
    "brand_mention", "sender_brand_mismatch",
]


# ---------------------------------------------------------------------------
# LightGBM adapter
# ---------------------------------------------------------------------------

class LightGBMAdapter:
    def __init__(self, checkpoint_dir: Path):
        import lightgbm as lgb
        import shap

        self._model = lgb.Booster(model_file=str(checkpoint_dir / "lgbm.txt"))

        with open(checkpoint_dir / "tfidf.pkl", "rb") as f:
            self._tfidf = pickle.load(f)

        cal = json.loads((checkpoint_dir / "calibration.json").read_text())
        self._platt_a = cal["a"]
        self._platt_b = cal["b"]

        manifest = json.loads((checkpoint_dir / "manifest.json").read_text())
        self._version = manifest["version"]

        # SHAP explainer — built once on load
        self._explainer = shap.TreeExplainer(self._model)

    def predict(self, text: str, features: dict[str, float]) -> ModelOutput:
        X_text = self._tfidf.transform([text])
        struct_row = np.array([[features.get(c, 0.0) for c in STRUCTURED_COLS]], dtype=float)
        X = hstack([X_text, csr_matrix(struct_row)])

        raw = self._model.predict(X)[0]
        p_phishing = float(expit(self._platt_a * raw + self._platt_b))
        p_spam = 1.0 - p_phishing

        # SHAP on structured features only (fast, inline)
        shap_vals = self._explainer.shap_values(struct_row)
        # shap_vals shape: (1, n_features) or list of two for binary
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1]  # phishing class
        attributions = {
            col: float(shap_vals[0][i])
            for i, col in enumerate(STRUCTURED_COLS)
        }

        return ModelOutput(
            spam_prob=p_spam,
            phishing_prob=p_phishing,
            feature_attributions=attributions,
        )

    def version(self) -> str:
        return self._version

    def model_type(self) -> str:
        return "lightgbm"
