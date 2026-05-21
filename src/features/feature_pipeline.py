"""feature_pipeline.py — orchestrates all feature extractors and counts missing features."""
from src.datasets.schema import EmailRecord
from src.features import attachment_features, brand_features, sender_features, text_stats, url_features

# Structured boolean/numeric feature fields (used for missing-feature counting)
_STRUCTURED_FIELDS = [
    "display_from_mismatch", "reply_to_mismatch", "free_email_sender",
    "url_count", "domain_count", "shortened_url_present", "suspicious_tld_present",
    "ip_literal_url", "url_entropy", "typosquatting_detected",
    "has_attachment", "executable_detected", "macro_detected",
    "subject_length", "body_length", "uppercase_ratio", "digit_ratio",
    "punctuation_density", "link_density", "brand_mention", "sender_brand_mismatch",
]


def run(rec: EmailRecord) -> EmailRecord:
    """Run all feature extractors on a record in-place. Returns the record."""
    sender_features.extract(rec)
    url_features.extract(rec)
    attachment_features.extract(rec)
    text_stats.extract(rec)
    brand_features.extract(rec)

    # Count fields that couldn't be populated (remain at default falsy/zero)
    # Only counts fields where the source data was genuinely absent
    missing = 0
    if not rec.sender_address:
        missing += 3  # sender group unavailable
    if not rec.urls and rec.body_text and "http" not in rec.body_text:
        pass  # no URLs is valid, not missing
    if not rec.body_text:
        missing += 4  # text stat group unavailable

    rec.missing_feature_count = missing
    return rec
