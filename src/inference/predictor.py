"""
Inference predictor: feature dict → prediction output.

Currently a STUB — returns realistic mock output.
Replace _run_model() with real model inference once checkpoint is available.

Expected feature dict keys (from email_parser.py):
    subject, body_text, sender_display_name, url_token_text,
    spf_result, dkim_result, dmarc_result,
    url_count, attachment_count, reply_to_mismatch,
    html_text_ratio, tld_risk_score,
    sender_seen_before, first_time_domain
"""

from __future__ import annotations
from typing import Any

CLASSES = ["spam", "junk", "phishing"]

# Routing thresholds (from confidence-and-explainability.md)
THRESHOLD_AUTO        = 0.90
THRESHOLD_AUTO_MONITOR = 0.75
THRESHOLD_REVIEW      = 0.55
PHISHING_OVERRIDE_PROB = 0.70

# High-weight signals that trigger security override
_HIGH_WEIGHT_SIGNALS = {
    "spf_fail_dkim_fail",
    "reply_to_mismatch",
    "high_risk_tld",
    "attachment_first_contact",
}


# ---------------------------------------------------------------------------
# Trust score
# ---------------------------------------------------------------------------

def _trust_score(probs: dict[str, float]) -> float:
    """trust_score = 0.6 * max_prob + 0.4 * margin  (normalised to 0–100)"""
    sorted_probs = sorted(probs.values(), reverse=True)
    max_prob = sorted_probs[0]
    margin   = sorted_probs[0] - sorted_probs[1]
    return round((0.6 * max_prob + 0.4 * margin) * 100, 1)


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route(probs: dict[str, float], trust: float, features: dict[str, Any]) -> str:
    top_class = max(probs, key=probs.__get__ if False else lambda k: probs[k])

    # Security override: phishing prob > 0.70 + any high-weight signal present
    active_signals = _active_high_weight_signals(features)
    if probs["phishing"] >= PHISHING_OVERRIDE_PROB and active_signals:
        return "Phishing"

    if trust > THRESHOLD_AUTO * 100:
        return top_class.capitalize()
    if trust > THRESHOLD_REVIEW * 100:
        return top_class.capitalize()  # auto-classify with monitoring flag at 75–90
    return "Analyst Review"


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


# ---------------------------------------------------------------------------
# Risk score
# ---------------------------------------------------------------------------

def _risk_score(probs: dict[str, float]) -> int:
    """Weighted risk: phishing carries highest weight."""
    raw = probs["phishing"] * 0.7 + probs["junk"] * 0.2 + probs["spam"] * 0.1
    return round(raw * 100)


# ---------------------------------------------------------------------------
# Stub model — replace this function with real model inference
# ---------------------------------------------------------------------------

def _run_model(features: dict[str, Any]) -> dict[str, float]:
    """
    STUB: returns heuristic probabilities based on signal strength.
    Replace with: load checkpoint → tokenise → forward pass → softmax.

    Returns:
        {"spam": float, "junk": float, "phishing": float}  (sum to 1.0)
    """
    # Accumulate a raw phishing signal weight (0.0 – 1.0)
    phishing_weight = 0.0
    if features.get("spf_result") == "fail":
        phishing_weight += 0.20
    if features.get("dkim_result") in ("fail", "none"):
        phishing_weight += 0.15
    if features.get("tld_risk_score", 1) >= 3:
        phishing_weight += 0.25
    if features.get("reply_to_mismatch"):
        phishing_weight += 0.20
    if features.get("attachment_count", 0) > 0 and features.get("first_time_domain"):
        phishing_weight += 0.20

    phishing_score = min(phishing_weight, 1.0)
    remaining      = 1.0 - phishing_score
    spam_share     = 0.6 if features.get("url_count", 0) > 5 else 0.4
    spam_score     = round(remaining * spam_share, 4)
    junk_score     = round(remaining * (1 - spam_share), 4)
    phishing_score = round(1.0 - spam_score - junk_score, 4)

    return {"phishing": phishing_score, "spam": spam_score, "junk": junk_score}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def predict(features: dict[str, Any]) -> dict[str, Any]:
    """
    Run inference on a parsed email feature dict.

    Args:
        features: output of email_parser.parse_eml()

    Returns:
        {
            label, trust_score, risk_score,
            class_probabilities,
            active_signals,
            monitoring_flag
        }
    """
    probs  = _run_model(features)
    trust  = _trust_score(probs)
    label  = _route(probs, trust, features)
    risk   = _risk_score(probs)
    signals = _active_high_weight_signals(features)

    return {
        "label":               label,
        "trust_score":         trust,
        "risk_score":          risk,
        "class_probabilities": probs,
        "active_signals":      signals,
        "monitoring_flag":     THRESHOLD_REVIEW * 100 < trust <= THRESHOLD_AUTO_MONITOR * 100,
    }
