"""
test_rule_summarizer.py — Tests for the SHAP → reasons mapper.

Covers: correct reasons per class, top_n cap, deduplication,
zero/negative SHAP values excluded, unknown features ignored,
empty attributions, ordering by SHAP magnitude.
"""
import pytest
from src.inference.adapter import STRUCTURED_COLS
from src.explainability.rule_summarizer import summarize


def _attrs(**kwargs) -> dict[str, float]:
    base = {col: 0.0 for col in STRUCTURED_COLS}
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# Basic correctness
# ---------------------------------------------------------------------------

def test_phishing_reason_returned_for_phishing_class():
    attrs = _attrs(reply_to_mismatch=0.8)
    reasons = summarize(attrs, "phishing")
    assert any("Reply-To" in r for r in reasons)


def test_spam_reason_returned_for_spam_class():
    attrs = _attrs(url_count=0.7)
    reasons = summarize(attrs, "spam")
    assert any("Promotional" in r for r in reasons)


def test_phishing_reason_not_shown_for_spam_class():
    # reply_to_mismatch has no spam reason — should be excluded
    attrs = _attrs(reply_to_mismatch=0.9)
    reasons = summarize(attrs, "spam")
    assert not any("Reply-To" in r for r in reasons)


def test_typosquatting_appears_for_phishing():
    attrs = _attrs(typosquatting_detected=0.9)
    reasons = summarize(attrs, "phishing")
    assert any("typosquatting" in r.lower() or "lookalike" in r.lower() for r in reasons)


def test_executable_appears_for_phishing():
    # executable_detected not in STRUCTURED_COLS (zero-variance, dropped at training)
    # rule_summarizer accepts any attribution dict
    attrs = {"executable_detected": 0.6}
    reasons = summarize(attrs, "phishing")
    assert any("Executable" in r for r in reasons)


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def test_zero_shap_excluded():
    attrs = _attrs(reply_to_mismatch=0.0)
    reasons = summarize(attrs, "phishing")
    assert not any("Reply-To" in r for r in reasons)


def test_negative_shap_excluded():
    attrs = _attrs(reply_to_mismatch=-0.5)
    reasons = summarize(attrs, "phishing")
    assert not any("Reply-To" in r for r in reasons)


def test_unknown_feature_ignored():
    attrs = _attrs()
    attrs["nonexistent_feature"] = 1.0
    # Should not raise and should not include garbage
    reasons = summarize(attrs, "phishing")
    assert isinstance(reasons, list)


def test_empty_attributions_returns_empty():
    reasons = summarize({}, "phishing")
    assert reasons == []


def test_all_zero_returns_empty():
    attrs = {col: 0.0 for col in STRUCTURED_COLS}
    reasons = summarize(attrs, "phishing")
    assert reasons == []


# ---------------------------------------------------------------------------
# Ordering and deduplication
# ---------------------------------------------------------------------------

def test_reasons_ordered_by_shap_magnitude():
    attrs = _attrs(reply_to_mismatch=0.3, typosquatting_detected=0.9)
    reasons = summarize(attrs, "phishing")
    # typosquatting has higher SHAP → should appear first
    typo_idx = next((i for i, r in enumerate(reasons) if "lookalike" in r.lower()), None)
    reply_idx = next((i for i, r in enumerate(reasons) if "Reply-To" in r), None)
    assert typo_idx is not None and reply_idx is not None
    assert typo_idx < reply_idx


def test_top_n_cap():
    attrs = _attrs(
        reply_to_mismatch=0.9,
        typosquatting_detected=0.8,
        ip_literal_url=0.7,
        shortened_url_present=0.6,
        suspicious_tld_present=0.5,
        display_from_mismatch=0.4,
    )
    reasons = summarize(attrs, "phishing", top_n=3)
    assert len(reasons) <= 3


def test_no_duplicate_reasons():
    # free_email_sender has same reason for phishing and spam — ensure no duplication
    attrs = _attrs(free_email_sender=0.9)
    reasons = summarize(attrs, "phishing")
    assert len(reasons) == len(set(reasons))


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_deterministic():
    attrs = _attrs(reply_to_mismatch=0.8, typosquatting_detected=0.6)
    r1 = summarize(attrs, "phishing")
    r2 = summarize(attrs, "phishing")
    assert r1 == r2
