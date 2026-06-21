"""
base.py — Shared protocol and types for all model adapters.

Every concrete adapter (LightGBMAdapter, TransformerAdapter, etc.) satisfies
the ModelAdapter protocol. The rest of the system (Predictor, API, tests)
depends only on this interface — never on a concrete adapter.
"""
from dataclasses import dataclass
from typing import Protocol


# Structured feature columns — single source of truth, must match training order.
STRUCTURED_COLS = [
    "display_from_mismatch", "reply_to_mismatch", "free_email_sender",
    "url_count", "domain_count", "shortened_url_present", "suspicious_tld_present",
    "ip_literal_url", "url_entropy", "typosquatting_detected",
    "has_attachment",
    "subject_length", "body_length", "uppercase_ratio", "digit_ratio",
    "punctuation_density", "link_density",
    "brand_mention", "sender_brand_mismatch",
]


@dataclass
class ModelOutput:
    spam_prob: float
    phishing_prob: float
    feature_attributions: dict[str, float]  # feature_name -> SHAP value


class ModelAdapter(Protocol):
    def predict(self, text: str, features: dict[str, float]) -> ModelOutput: ...
    def version(self) -> str: ...
    def model_type(self) -> str: ...
