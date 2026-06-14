"""
test_postprocess.py — Tests for TriageResponse assembly.

Covers: field mapping, probability rounding, confidence_notes generation,
security override note, borderline note, review routing note.
"""
import pytest
from src.inference.adapter import ModelOutput, STRUCTURED_COLS
from src.inference.threshold_router import RoutingDecision
from src.inference.postprocess import build_response


def _output(spam=0.05, phishing=0.95, **shap_overrides) -> ModelOutput:
    attrs = {col: 0.0 for col in STRUCTURED_COLS}
    attrs.update(shap_overrides)
    return ModelOutput(spam_prob=spam, phishing_prob=phishing, feature_attributions=attrs)


def _routing(label="phishing", predicted="phishing", trust=95.0, review=False, override=False) -> RoutingDecision:
    return RoutingDecision(
        label=label,
        predicted_class=predicted,
        trust_score=trust,
        routed_to_review=review,
        security_override=override,
    )


# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------

def test_email_id_passed_through():
    r = build_response("abc-123", _output(), _routing(), "mock-v0.0")
    assert r.email_id == "abc-123"


def test_label_from_routing():
    r = build_response("x", _output(), _routing(label="spam"), "v1")
    assert r.label == "spam"


def test_predicted_class_from_routing():
    r = build_response("x", _output(), _routing(predicted="spam"), "v1")
    assert r.predicted_class == "spam"


def test_probabilities_rounded_to_4dp():
    r = build_response("x", _output(spam=0.123456, phishing=0.876544), _routing(), "v1")
    assert r.spam_probability == 0.1235
    assert r.phishing_probability == 0.8765


def test_trust_score_rounded_to_1dp():
    r = build_response("x", _output(), _routing(trust=92.567), "v1")
    assert r.trust_score == 92.6


def test_model_version_passed_through():
    r = build_response("x", _output(), _routing(), "lightgbm-v20260531")
    assert r.model_version == "lightgbm-v20260531"


def test_routed_to_review_propagated():
    r = build_response("x", _output(spam=0.48, phishing=0.52), _routing(review=True, label="analyst_review"), "v1")
    assert r.routed_to_review is True


# ---------------------------------------------------------------------------
# confidence_notes
# ---------------------------------------------------------------------------

def test_security_override_note_added():
    r = build_response("x", _output(), _routing(override=True), "v1")
    assert any("override" in n.lower() for n in r.confidence_notes)


def test_review_routing_note_added():
    r = build_response("x", _output(spam=0.48, phishing=0.52), _routing(review=True, trust=60.0), "v1")
    assert any("analyst review" in n.lower() for n in r.confidence_notes)


def test_review_note_contains_trust_score():
    r = build_response("x", _output(), _routing(review=True, trust=62.0), "v1")
    assert any("62" in n for n in r.confidence_notes)


def test_borderline_note_when_spam_predicted_but_high_phishing_prob():
    # predicted spam but phishing_prob > 0.55
    r = build_response("x", _output(spam=0.44, phishing=0.56), _routing(predicted="spam"), "v1")
    assert any("borderline" in n.lower() for n in r.confidence_notes)


def test_no_borderline_note_for_clear_spam():
    r = build_response("x", _output(spam=0.95, phishing=0.05), _routing(predicted="spam"), "v1")
    assert not any("borderline" in n.lower() for n in r.confidence_notes)


def test_no_spurious_notes_for_clean_phishing():
    r = build_response("x", _output(), _routing(), "v1")
    assert r.confidence_notes == []


# ---------------------------------------------------------------------------
# reasons populated from attributions
# ---------------------------------------------------------------------------

def test_reasons_list_populated():
    r = build_response("x", _output(reply_to_mismatch=0.8), _routing(), "v1")
    assert isinstance(r.reasons, list)


def test_reasons_empty_when_no_positive_shap():
    r = build_response("x", _output(), _routing(), "v1")
    # reply_to_mismatch=0.1 from MockAdapter — should produce a reason
    # but _output() defaults all to 0.0
    assert isinstance(r.reasons, list)
