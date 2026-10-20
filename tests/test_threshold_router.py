"""
test_threshold_router.py — Tests for trust score calculation and routing logic.

Covers: trust score formula, all routing bands, security override conditions,
predicted_class assignment, edge cases.
"""
import pytest
from src.inference.threshold_router import route, HIGH_WEIGHT_SIGNALS, RoutingDecision


# ---------------------------------------------------------------------------
# Trust score
# ---------------------------------------------------------------------------

def test_trust_score_perfect_phishing():
    r = route(0.0, 1.0, {})
    # max_prob=1.0, margin=1.0 → (0.6*1.0 + 0.4*1.0)*100 = 100
    assert r.trust_score == pytest.approx(100.0)


def test_trust_score_perfect_spam():
    r = route(1.0, 0.0, {})
    assert r.trust_score == pytest.approx(100.0)


def test_trust_score_perfectly_ambiguous():
    r = route(0.5, 0.5, {})
    # max_prob=0.5, margin=0.0 → (0.6*0.5 + 0.4*0.0)*100 = 30
    assert r.trust_score == pytest.approx(30.0)


def test_trust_score_always_in_range():
    import numpy as np
    for p in np.linspace(0.0, 1.0, 21):
        r = route(1 - p, p, {})
        assert 0.0 <= r.trust_score <= 100.0


# ---------------------------------------------------------------------------
# Routing bands
# ---------------------------------------------------------------------------

def test_high_confidence_phishing_auto_classifies():
    r = route(0.02, 0.98, {})
    assert r.label == "phishing"
    assert r.routed_to_review is False
    assert r.trust_score > 90


def test_high_confidence_spam_auto_classifies():
    r = route(0.98, 0.02, {})
    assert r.label == "spam"
    assert r.routed_to_review is False


def test_monitor_band_auto_classifies_not_review():
    # trust score should land in 75-90 band
    # max_prob=0.88, margin=0.76 → (0.6*0.88 + 0.4*0.76)*100 = 83.2
    r = route(0.12, 0.88, {})
    assert r.routed_to_review is False
    assert r.label in ("spam", "phishing")
    assert 75 < r.trust_score <= 90


def test_low_confidence_routes_to_analyst_review():
    # max_prob=0.62, margin=0.24 → (0.6*0.62 + 0.4*0.24)*100 = 46.8 — priority review
    # Use values that land in 55-75
    # max_prob=0.68, margin=0.36 → (0.6*0.68 + 0.4*0.36)*100 = 55.2 — just above review threshold
    r = route(0.32, 0.68, {})
    assert r.routed_to_review is True
    assert r.label in ("analyst_review", "priority_analyst_review")


def test_very_low_confidence_priority_review():
    r = route(0.5, 0.5, {})
    assert r.label == "priority_analyst_review"
    assert r.routed_to_review is True


# ---------------------------------------------------------------------------
# Predicted class
# ---------------------------------------------------------------------------

def test_predicted_class_phishing_when_phishing_higher():
    r = route(0.3, 0.7, {})
    assert r.predicted_class == "phishing"


def test_predicted_class_spam_when_spam_higher():
    r = route(0.8, 0.2, {})
    assert r.predicted_class == "spam"


def test_predicted_class_phishing_on_tie():
    # phishing >= spam → phishing
    r = route(0.5, 0.5, {})
    assert r.predicted_class == "phishing"


# ---------------------------------------------------------------------------
# Security override
# ---------------------------------------------------------------------------

def test_security_override_triggers_with_high_prob_and_signal():
    features = {"typosquatting_detected": 1.0}
    r = route(0.25, 0.75, features)
    assert r.security_override is True
    assert r.label == "phishing"
    assert r.routed_to_review is False


def test_security_override_requires_high_prob():
    # phishing_prob = 0.65, below 0.70 threshold
    features = {"typosquatting_detected": 1.0}
    r = route(0.35, 0.65, features)
    assert r.security_override is False


def test_security_override_requires_signal():
    # phishing_prob > 0.70 but no high-weight signals
    r = route(0.25, 0.75, {})
    assert r.security_override is False


def test_all_high_weight_signals_trigger_override():
    for signal in HIGH_WEIGHT_SIGNALS:
        r = route(0.25, 0.75, {signal: 1.0})
        assert r.security_override is True, f"Signal {signal} did not trigger override"


def test_security_override_overrides_routing_band():
    # Even if trust score is borderline, override forces phishing
    features = {"ip_literal_url": 1.0}
    r = route(0.28, 0.72, features)
    assert r.label == "phishing"
    assert r.security_override is True


# ---------------------------------------------------------------------------
# Custom thresholds
# ---------------------------------------------------------------------------

def test_custom_thresholds_respected():
    # With threshold_auto=50, everything above 50 auto-classifies
    r = route(0.32, 0.68, {}, threshold_auto=50.0, threshold_monitor=40.0, threshold_review=30.0)
    assert r.routed_to_review is False
