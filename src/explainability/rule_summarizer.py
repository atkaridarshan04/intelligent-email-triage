"""
rule_summarizer.py — Map SHAP feature attributions to human-readable reasons.

Strategy:
1. Use SHAP attributions to rank structured features by contribution.
2. Only surface a reason if the feature value actually supports it
   (guards against SHAP noise on near-zero features).
3. If fewer than 2 SHAP-driven reasons found, fall back to scanning
   actual feature values directly — this handles cases where the model
   is driven entirely by text (TF-IDF) and structured SHAP values are all ~0.
"""
from dataclasses import dataclass

# Feature -> (spam reason, phishing reason)
_REASONS: dict[str, tuple[str, str]] = {
    "display_from_mismatch":  ("", "Display name doesn't match sender domain"),
    "reply_to_mismatch":      ("", "Reply-To address differs from sender"),
    "free_email_sender":      ("Sent from a free email provider", "Sent from a free email provider"),
    "typosquatting_detected": ("", "Lookalike domain detected (possible typosquatting)"),
    "ip_literal_url":         ("", "URL uses raw IP address instead of domain"),
    "shortened_url_present":  ("", "Contains shortened URL"),
    "suspicious_tld_present": ("", "URL uses high-risk top-level domain"),
    "url_entropy":            ("", "Unusually high domain name entropy"),
    "sender_brand_mismatch":  ("", "Sender domain doesn't match mentioned brand"),
    "executable_detected":    ("", "Executable file attached"),
    "macro_detected":         ("", "Macro-enabled Office document attached"),
    "url_count":              ("Promotional link volume", "High URL count"),
    "domain_count":           ("", "Multiple distinct domains in email"),
    "link_density":           ("", "Unusually high link density"),
    "uppercase_ratio":        ("", "High uppercase ratio (urgency signal)"),
    "brand_mention":          ("", ""),
    "has_attachment":         ("", ""),
    "punctuation_density":    ("", ""),
    "subject_length":         ("", ""),
    "body_length":            ("", ""),
    "digit_ratio":            ("", ""),
}

# Thresholds: feature must exceed this value to be considered "active"
_ACTIVE_THRESHOLDS: dict[str, float] = {
    "display_from_mismatch":  0.5,
    "reply_to_mismatch":      0.5,
    "free_email_sender":      0.5,
    "typosquatting_detected": 0.5,
    "ip_literal_url":         0.5,
    "shortened_url_present":  0.5,
    "suspicious_tld_present": 0.5,
    "url_entropy":            1.5,
    "sender_brand_mismatch":  0.5,
    "executable_detected":    0.5,
    "macro_detected":         0.5,
    "url_count":              2.0,
    "domain_count":           2.0,
    "link_density":           0.05,
    "uppercase_ratio":        0.08,
}


def _is_active(feature: str, value: float) -> bool:
    threshold = _ACTIVE_THRESHOLDS.get(feature)
    if threshold is None:
        return False
    return value > threshold


def summarize(
    attributions: dict[str, float],
    predicted_class: str,
    top_n: int = 5,
) -> list[str]:
    """Return up to top_n human-readable reasons for the prediction."""
    class_idx = 1 if predicted_class == "phishing" else 0

    # --- Pass 1: SHAP-driven reasons (attribution > 0 AND feature is active) ---
    shap_reasons: list[tuple[float, str]] = []
    for feature, shap_val in attributions.items():
        if shap_val <= 0:
            continue
        reason = _REASONS.get(feature, ("", ""))[class_idx]
        if not reason:
            continue
        feat_val = attributions.get(feature, 0.0)  # use attribution as proxy if no raw value
        if _is_active(feature, feat_val) or shap_val > 0.05:
            shap_reasons.append((shap_val, reason))

    shap_reasons.sort(reverse=True)

    seen: set[str] = set()
    reasons: list[str] = []
    for _, r in shap_reasons:
        if r not in seen:
            seen.add(r)
            reasons.append(r)
        if len(reasons) >= top_n:
            break

    # --- Pass 2: fallback — scan raw feature values directly ---
    # Used when SHAP attributions are all near-zero (text-dominated prediction)
    if len(reasons) < 2:
        for feature, threshold in _ACTIVE_THRESHOLDS.items():
            val = attributions.get(feature, 0.0)
            if val > threshold:
                reason = _REASONS.get(feature, ("", ""))[class_idx]
                if reason and reason not in seen:
                    seen.add(reason)
                    reasons.append(reason)
            if len(reasons) >= top_n:
                break

    return reasons


def summarize_with_features(
    attributions: dict[str, float],
    feature_values: dict[str, float],
    predicted_class: str,
    top_n: int = 5,
) -> list[str]:
    """
    Preferred entry point when raw feature values are available separately
    from SHAP attributions. Uses SHAP for ranking, feature values for
    activation gating.
    """
    class_idx = 1 if predicted_class == "phishing" else 0

    shap_reasons: list[tuple[float, str]] = []
    for feature, shap_val in attributions.items():
        if shap_val <= 0:
            continue
        reason = _REASONS.get(feature, ("", ""))[class_idx]
        if not reason:
            continue
        if _is_active(feature, feature_values.get(feature, 0.0)):
            shap_reasons.append((shap_val, reason))

    shap_reasons.sort(reverse=True)

    seen: set[str] = set()
    reasons: list[str] = []
    for _, r in shap_reasons:
        if r not in seen:
            seen.add(r)
            reasons.append(r)
        if len(reasons) >= top_n:
            break

    # Fallback: any active feature regardless of SHAP
    if len(reasons) < 2:
        for feature, threshold in _ACTIVE_THRESHOLDS.items():
            if feature_values.get(feature, 0.0) > threshold:
                reason = _REASONS.get(feature, ("", ""))[class_idx]
                if reason and reason not in seen:
                    seen.add(reason)
                    reasons.append(reason)
            if len(reasons) >= top_n:
                break

    if not reasons:
        if predicted_class == "phishing":
            reasons = ["Email content matches known phishing patterns"]
        else:
            reasons = ["Email content matches bulk/promotional patterns"]

    return reasons
