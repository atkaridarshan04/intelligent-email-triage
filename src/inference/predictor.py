"""
Inference predictor: feature dict → prediction output.

Loads artifacts/best.pt (state dict from spam-phishing.ipynb training run)
and runs a real forward pass for every prediction.

Expected feature dict keys (from email_parser.py):
    subject, body_text, sender_display_name, url_token_text,
    spf_result, dkim_result, dmarc_result,
    url_count, attachment_count, reply_to_mismatch,
    html_text_ratio, tld_risk_score,
    sender_seen_before, first_time_domain
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import torch
from transformers import RobertaTokenizerFast

from src.models.model import AUTH_MAP, CLASSES, SPF_MAP, EmailTriageModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_CHECKPOINT    = Path(__file__).parents[2] / "outputs" / "best"
_ROBERTA_NAME  = "roberta-base"
_MAX_LENGTH    = 256

# Routing thresholds (from confidence-and-explainability.md)
THRESHOLD_AUTO         = 0.90
THRESHOLD_AUTO_MONITOR = 0.75
THRESHOLD_REVIEW       = 0.55
PHISHING_OVERRIDE_PROB = 0.70

_URL_REGEX = re.compile(r"https?://\S+|www\.\S+")

# ---------------------------------------------------------------------------
# Model singleton
# ---------------------------------------------------------------------------

_model: EmailTriageModel | None = None
_tokenizer: RobertaTokenizerFast | None = None
_device: torch.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_model() -> tuple[EmailTriageModel, RobertaTokenizerFast]:
    global _model, _tokenizer
    if _model is None:
        _tokenizer = RobertaTokenizerFast.from_pretrained(_ROBERTA_NAME)
        _model = EmailTriageModel(roberta_name=_ROBERTA_NAME)
        state = torch.load(_CHECKPOINT, map_location=_device, weights_only=True)
        _model.load_state_dict(state)
        _model.to(_device)
        _model.eval()
    return _model, _tokenizer


# ---------------------------------------------------------------------------
# Feature encoding (mirrors notebook's encode_metadata)
# ---------------------------------------------------------------------------

def _encode_metadata(features: dict[str, Any]) -> torch.Tensor:
    vec = np.array([
        SPF_MAP.get(features.get("spf_result", "none"), -1.0),
        AUTH_MAP.get(features.get("dkim_result", "none"), -1.0),
        AUTH_MAP.get(features.get("dmarc_result", "none"), -1.0),
        float(features.get("url_count", 0)),
        float(features.get("attachment_count", 0)),
        float(bool(features.get("reply_to_mismatch", False))),
        float(features.get("html_text_ratio", 0.0)),
        float(features.get("tld_risk_score", 1.0)),
        float(bool(features.get("sender_seen_before", False))),
        float(bool(features.get("first_time_domain", True))),
    ], dtype=np.float32)
    return torch.tensor(vec).unsqueeze(0)  # (1, 10)


def _normalize(text: str | None) -> str:
    return _URL_REGEX.sub("<URL>", text or "")


def _build_text(features: dict[str, Any], sep: str) -> str:
    return (
        _normalize(features.get("subject")) + f" {sep} " +
        _normalize(features.get("sender_display_name")) + f" {sep} " +
        _normalize(features.get("url_token_text")) + f" {sep} " +
        _normalize(features.get("body_text"))
    )


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _trust_score(probs: dict[str, float]) -> float:
    sorted_p = sorted(probs.values(), reverse=True)
    return round((0.6 * sorted_p[0] + 0.4 * (sorted_p[0] - sorted_p[1])) * 100, 1)


def _risk_score(probs: dict[str, float]) -> int:
    return round((probs["phishing"] * 0.7 + probs["junk"] * 0.2 + probs["spam"] * 0.1) * 100)


def _active_high_weight_signals(features: dict[str, Any]) -> list[str]:
    active = []
    if features.get("spf_result") == "fail" and features.get("dkim_result") in ("fail", "none"):
        active.append("spf_fail_dkim_fail")
    if features.get("reply_to_mismatch"):
        active.append("reply_to_mismatch")
    if features.get("tld_risk_score", 1) >= 3:
        active.append("high_risk_tld")
    if features.get("attachment_count", 0) > 0 and features.get("first_time_domain"):
        active.append("attachment_first_contact")
    return active


def _route(probs: dict[str, float], trust: float, features: dict[str, Any]) -> str:
    top_class = max(probs, key=lambda k: probs[k])
    if probs["phishing"] >= PHISHING_OVERRIDE_PROB and _active_high_weight_signals(features):
        return "Phishing"
    if trust > THRESHOLD_REVIEW * 100:
        return top_class.capitalize()
    return "Analyst Review"


# ---------------------------------------------------------------------------
# Core inference
# ---------------------------------------------------------------------------

def _run_model(features: dict[str, Any]) -> dict[str, float]:
    model, tokenizer = _load_model()

    text = _build_text(features, tokenizer.sep_token)
    enc  = tokenizer(
        text,
        max_length=_MAX_LENGTH,
        truncation=True,
        padding="max_length",
        return_tensors="pt",
    )

    input_ids      = enc["input_ids"].to(_device)
    attention_mask = enc["attention_mask"].to(_device)
    metadata       = _encode_metadata(features).to(_device)

    with torch.no_grad():
        logits = model(input_ids, attention_mask, metadata)
        probs  = torch.softmax(logits, dim=-1).squeeze(0).cpu().tolist()

    return {cls: round(probs[i], 6) for i, cls in enumerate(CLASSES)}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def predict(features: dict[str, Any]) -> dict[str, Any]:
    """
    Run inference on a parsed email feature dict.

    Args:
        features: output of email_parser.parse_eml()

    Returns:
        {label, trust_score, risk_score, class_probabilities, active_signals, monitoring_flag}
    """
    probs   = _run_model(features)
    trust   = _trust_score(probs)
    label   = _route(probs, trust, features)
    risk    = _risk_score(probs)
    signals = _active_high_weight_signals(features)

    return {
        "label":               label,
        "trust_score":         trust,
        "risk_score":          risk,
        "class_probabilities": probs,
        "active_signals":      signals,
        "monitoring_flag":     THRESHOLD_REVIEW * 100 < trust <= THRESHOLD_AUTO_MONITOR * 100,
    }
