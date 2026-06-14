"""
threshold_router.py — Stateless confidence routing.

Inputs: spam_prob, phishing_prob (calibrated floats 0–1)
Output: RoutingDecision
"""
from dataclasses import dataclass
from typing import Literal

# High-weight signal names — used by security override check
HIGH_WEIGHT_SIGNALS = {
    "typosquatting_detected",
    "ip_literal_url",
    "reply_to_mismatch",
    "suspicious_tld_present",
    "sender_brand_mismatch",
    "executable_detected",
    "macro_detected",
}

RoutingLabel = Literal["spam", "phishing", "analyst_review", "priority_analyst_review"]


@dataclass
class RoutingDecision:
    label: RoutingLabel           # final routed label
    predicted_class: str          # model's lean regardless of routing
    trust_score: float            # 0–100
    routed_to_review: bool
    security_override: bool


def route(
    spam_prob: float,
    phishing_prob: float,
    features: dict[str, float],
    *,
    w1: float = 0.6,
    w2: float = 0.4,
    threshold_auto: float = 90.0,
    threshold_monitor: float = 75.0,
    threshold_review: float = 55.0,
    override_phishing_threshold: float = 0.70,
) -> RoutingDecision:
    max_prob = max(spam_prob, phishing_prob)
    margin = abs(phishing_prob - spam_prob)
    trust = (w1 * max_prob + w2 * margin) * 100.0

    predicted_class = "phishing" if phishing_prob >= spam_prob else "spam"

    # Security override: high phishing probability + any high-weight signal
    security_override = (
        phishing_prob > override_phishing_threshold
        and any(features.get(s, 0.0) for s in HIGH_WEIGHT_SIGNALS)
    )
    if security_override:
        return RoutingDecision(
            label="phishing",
            predicted_class="phishing",
            trust_score=trust,
            routed_to_review=False,
            security_override=True,
        )

    if trust > threshold_auto:
        label = predicted_class
        routed_to_review = False
    elif trust > threshold_monitor:
        label = predicted_class
        routed_to_review = False
    elif trust > threshold_review:
        label = "analyst_review"
        routed_to_review = True
    else:
        label = "priority_analyst_review"
        routed_to_review = True

    return RoutingDecision(
        label=label,
        predicted_class=predicted_class,
        trust_score=trust,
        routed_to_review=routed_to_review,
        security_override=False,
    )
