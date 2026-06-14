"""
rule_summarizer.py — Map SHAP feature attributions to human-readable reasons.

Deterministic: same attributions always produce the same reasons.
Only includes features with meaningful positive contribution toward
the predicted class.
"""
from dataclasses import dataclass

# Feature -> (spam reason, phishing reason)
# class_idx: spam=0, phishing=1
_REASONS: dict[str, tuple[str, str]] = {
    "display_from_mismatch":    ("", "Display name doesn't match sender domain"),
    "reply_to_mismatch":        ("", "Reply-To address differs from sender"),
    "free_email_sender":        ("Sent from a free email provider", "Sent from a free email provider"),
    "typosquatting_detected":   ("", "Lookalike domain detected (possible typosquatting)"),
    "ip_literal_url":           ("", "URL uses raw IP address instead of domain"),
    "shortened_url_present":    ("", "Contains shortened URL"),
    "suspicious_tld_present":   ("", "URL uses high-risk top-level domain"),
    "url_entropy":              ("", "Unusually high domain name entropy"),
    "brand_mention":            ("", ""),
    "sender_brand_mismatch":    ("", "Sender domain doesn't match mentioned brand"),
    "executable_detected":      ("", "Executable file attached"),
    "macro_detected":           ("", "Macro-enabled Office document attached"),
    "has_attachment":           ("", ""),
    "url_count":                ("Promotional link volume", "High URL count"),
    "domain_count":             ("", "Multiple distinct domains in email"),
    "link_density":             ("", "Unusually high link density"),
    "uppercase_ratio":          ("", "High uppercase ratio (urgency signal)"),
    "punctuation_density":      ("", ""),
    "subject_length":           ("", ""),
    "body_length":              ("", ""),
    "digit_ratio":              ("", ""),
}


def summarize(
    attributions: dict[str, float],
    predicted_class: str,
    top_n: int = 5,
) -> list[str]:
    """Return top_n human-readable reasons for the prediction."""
    class_idx = 1 if predicted_class == "phishing" else 0
    scored = []
    for feature, shap_val in attributions.items():
        if feature not in _REASONS:
            continue
        if shap_val <= 0:
            continue
        reason = _REASONS[feature][class_idx]
        if reason:
            scored.append((shap_val, reason))

    scored.sort(reverse=True)
    # deduplicate while preserving order
    seen: set[str] = set()
    reasons: list[str] = []
    for _, r in scored:
        if r not in seen:
            seen.add(r)
            reasons.append(r)
        if len(reasons) >= top_n:
            break
    return reasons
