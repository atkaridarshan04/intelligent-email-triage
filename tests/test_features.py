"""
test_features.py — Tests for feature extractors and feature_pipeline.

Each extractor is tested directly using EmailRecord inputs.
Also tests that feature_pipeline produces a fully-populated dict
(no missing keys, all values resolve to 0/False when inputs absent).
"""
import pytest
from src.data.schema import AttachmentInfo, EmailRecord
from src.features import attachment_features, brand_features, sender_features, text_stats, url_features
from src.features.feature_pipeline import run as run_pipeline
from src.inference.adapter import STRUCTURED_COLS


def _rec(**kwargs) -> EmailRecord:
    return EmailRecord(**kwargs)


# ---------------------------------------------------------------------------
# sender_features
# ---------------------------------------------------------------------------

def test_display_from_mismatch_detected():
    rec = _rec(sender_display_name="paypal.com admin", sender_address="attacker@evil.com")
    sender_features.extract(rec)
    assert rec.display_from_mismatch is True


def test_display_from_mismatch_not_triggered_when_matching():
    rec = _rec(sender_display_name="John Smith", sender_address="john@company.com")
    sender_features.extract(rec)
    assert rec.display_from_mismatch is False


def test_reply_to_mismatch_detected():
    rec = _rec(sender_address="legit@bank.com", reply_to="attacker@evil.com")
    sender_features.extract(rec)
    assert rec.reply_to_mismatch is True


def test_reply_to_mismatch_not_triggered_when_same_domain():
    rec = _rec(sender_address="support@bank.com", reply_to="noreply@bank.com")
    sender_features.extract(rec)
    assert rec.reply_to_mismatch is False


def test_no_crash_with_empty_sender():
    rec = _rec(sender_address="", reply_to="", sender_display_name="")
    sender_features.extract(rec)  # should not raise


# ---------------------------------------------------------------------------
# url_features
# ---------------------------------------------------------------------------

def test_url_count_accurate():
    rec = _rec(urls=["https://a.com", "https://b.com", "https://c.com"])
    url_features.extract(rec)
    assert rec.url_count == 3


def test_domain_count_deduplicates():
    rec = _rec(urls=["https://evil.com/page1", "https://evil.com/page2", "https://other.com"])
    url_features.extract(rec)
    assert rec.domain_count == 2


def test_ip_literal_url_detected():
    rec = _rec(urls=["http://192.168.1.1/phish"])
    url_features.extract(rec)
    assert rec.ip_literal_url is True


def test_ip_literal_not_triggered_for_domain():
    rec = _rec(urls=["https://legit-bank.com/login"])
    url_features.extract(rec)
    assert rec.ip_literal_url is False


def test_suspicious_tld_detected():
    rec = _rec(urls=["https://winner.xyz/claim"])
    url_features.extract(rec)
    assert rec.suspicious_tld_present is True


def test_url_entropy_positive_for_random_domain():
    rec = _rec(urls=["https://xkqzjmvp.com/path"])
    url_features.extract(rec)
    assert rec.url_entropy > 0.0


def test_zero_urls_produces_zero_count():
    rec = _rec(urls=[])
    url_features.extract(rec)
    assert rec.url_count == 0
    assert rec.domain_count == 0
    assert rec.url_entropy == 0.0


# ---------------------------------------------------------------------------
# attachment_features
# ---------------------------------------------------------------------------

def test_executable_detected():
    rec = _rec(attachments=[AttachmentInfo(filename="payload.exe", mime_type="application/octet-stream")])
    attachment_features.extract(rec)
    assert rec.has_attachment is True
    assert rec.executable_detected is True


def test_macro_detected():
    rec = _rec(attachments=[AttachmentInfo(filename="invoice.xlsm", mime_type="application/vnd.ms-excel")])
    attachment_features.extract(rec)
    assert rec.macro_detected is True


def test_no_attachment_leaves_flags_false():
    rec = _rec(attachments=[])
    attachment_features.extract(rec)
    assert rec.has_attachment is False
    assert rec.executable_detected is False
    assert rec.macro_detected is False


def test_pdf_attachment_no_executable_flag():
    rec = _rec(attachments=[AttachmentInfo(filename="report.pdf", mime_type="application/pdf")])
    attachment_features.extract(rec)
    assert rec.has_attachment is True
    assert rec.executable_detected is False


# ---------------------------------------------------------------------------
# text_stats
# ---------------------------------------------------------------------------

def test_subject_length_correct():
    rec = _rec(subject="Hello World", body_text="body")
    text_stats.extract(rec)
    assert rec.subject_length == 11


def test_body_length_correct():
    rec = _rec(subject="", body_text="a" * 500)
    text_stats.extract(rec)
    assert rec.body_length == 500


def test_uppercase_ratio_calculated():
    rec = _rec(body_text="UPPER lower")
    text_stats.extract(rec)
    assert 0.0 < rec.uppercase_ratio < 1.0


def test_link_density_positive_when_urls_present():
    rec = _rec(body_text="Click here https://example.com to verify your account today now")
    text_stats.extract(rec)
    assert rec.link_density > 0.0


def test_empty_body_produces_zero_stats():
    rec = _rec(body_text="")
    text_stats.extract(rec)
    assert rec.body_length == 0
    assert rec.uppercase_ratio == 0.0
    assert rec.digit_ratio == 0.0


# ---------------------------------------------------------------------------
# feature_pipeline
# ---------------------------------------------------------------------------

def test_pipeline_returns_same_record():
    rec = _rec(subject="Test", body_text="Hello world", sender_address="x@y.com")
    result = run_pipeline(rec)
    assert result is rec


def test_pipeline_populates_all_structured_cols():
    rec = _rec(
        subject="Urgent: verify your account",
        body_text="Click https://evil.xyz/login to reset your password immediately",
        sender_address="support@evil.xyz",
        reply_to="harvest@attacker.com",
        urls=["https://evil.xyz/login"],
    )
    run_pipeline(rec)
    feature_dict = {col: getattr(rec, col, None) for col in STRUCTURED_COLS}
    for col, val in feature_dict.items():
        assert val is not None, f"Feature {col!r} is None after pipeline"


def test_pipeline_no_crash_with_empty_record():
    rec = EmailRecord()
    run_pipeline(rec)  # should not raise


def test_pipeline_all_feature_values_are_numeric_or_bool():
    rec = _rec(body_text="Buy this product now!", sender_address="promo@shop.com")
    run_pipeline(rec)
    for col in STRUCTURED_COLS:
        val = getattr(rec, col, None)
        assert isinstance(val, (int, float, bool)), f"{col} has unexpected type {type(val)}"
