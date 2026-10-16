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

RoutingLabel = Literal[
    "spam",
    "phishing",
    "analyst_review",
    "priority_analyst_review",
    "legitimate_benign",
]


@dataclass
class RoutingDecision:
    label: RoutingLabel           # final routed label
    predicted_class: str          # model's lean regardless of routing
    trust_score: float            # 0–100
    routed_to_review: bool
    security_override: bool
    fast_path_hit: bool = False
    fast_path_info: dict | None = None


def route(
    spam_prob: float,
    phishing_prob: float,
    features: dict[str, float],
    *,
    fast_path_match: dict | None = None,
    w1: float = 0.6,
    w2: float = 0.4,
    threshold_auto: float = 90.0,
    threshold_monitor: float = 75.0,
    threshold_review: float = 55.0,
    override_phishing_threshold: float = 0.70,
) -> RoutingDecision:
    # 0. Fast-Path Episodic Memory match (Instant Analyst Verdict)
    if fast_path_match:
        verdict = fast_path_match.get("verdict", "").lower().strip()
        if verdict in ("phish", "phishing"):
            return RoutingDecision(
                label="phishing",
                predicted_class="phishing",
                trust_score=100.0,
                routed_to_review=False,
                security_override=True,
                fast_path_hit=True,
                fast_path_info=fast_path_match,
            )
        elif verdict in ("benign", "legitimate", "safe"):
            return RoutingDecision(
                label="legitimate_benign",
                predicted_class="legitimate_benign",
                trust_score=100.0,
                routed_to_review=False,
                security_override=False,
                fast_path_hit=True,
                fast_path_info=fast_path_match,
            )
        elif verdict in ("spam", "noise", "junk"):
            return RoutingDecision(
                label="spam",
                predicted_class="spam",
                trust_score=100.0,
                routed_to_review=False,
                security_override=False,
                fast_path_hit=True,
                fast_path_info=fast_path_match,
            )

    # 1. Threat-Absent Authorized Internal Benign Check (Corporate Employee False Alarm Handler)
    # When an email mentions an authorized brand matching sender domain (brand_mention=True, sender_brand_mismatch=False),
    # has NO free email sender, NO header spoofing, NO attachments, and zero high-weight threat signals,
    # it represents a legitimate internal corporate communication.
    is_authorized_clean_internal = (
        bool(features.get("brand_mention", False))
        and not bool(features.get("sender_brand_mismatch", False))
        and not bool(features.get("free_email_sender", False))
        and not bool(features.get("display_from_mismatch", False))
        and not bool(features.get("reply_to_mismatch", False))
        and not bool(features.get("has_attachment", False))
        and not bool(features.get("shortened_url_present", False))
        and not bool(features.get("suspicious_tld_present", False))
        and not any(bool(features.get(s, 0.0)) for s in HIGH_WEIGHT_SIGNALS)
    )
    if is_authorized_clean_internal:
        return RoutingDecision(
            label="legitimate_benign",
            predicted_class="legitimate_benign",
            trust_score=95.0,
            routed_to_review=False,
            security_override=False,
        )

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
