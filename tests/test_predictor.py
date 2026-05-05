"""
Tests for src/inference/predictor.py

Run:
    python -m pytest tests/test_predictor.py -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.inference.predictor import predict

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def base_features(**overrides):
    f = {
        "subject": "Test", "body_text": "Hello", "sender_display_name": "x@legit.com",
        "url_token_text": "", "spf_result": "pass", "dkim_result": "pass",
        "dmarc_result": "pass", "url_count": 0, "attachment_count": 0,
        "reply_to_mismatch": False, "html_text_ratio": 1.0, "tld_risk_score": 1,
        "sender_seen_before": False, "first_time_domain": True,
    }
    f.update(overrides)
    return f


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

def test_output_keys():
    result = predict(base_features())
    assert {"label", "trust_score", "risk_score", "class_probabilities",
            "active_signals", "monitoring_flag"} == set(result.keys())

def test_probabilities_sum_to_one():
    probs = predict(base_features())["class_probabilities"]
    assert abs(sum(probs.values()) - 1.0) < 0.01

def test_trust_score_range():
    trust = predict(base_features())["trust_score"]
    assert 0 <= trust <= 100

def test_risk_score_range():
    risk = predict(base_features())["risk_score"]
    assert 0 <= risk <= 100


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def test_clean_email_not_phishing():
    result = predict(base_features(first_time_domain=False))
    assert result["label"] != "Phishing"

def test_high_risk_signals_route_phishing():
    result = predict(base_features(
        spf_result="fail", dkim_result="none",
        tld_risk_score=3, reply_to_mismatch=True,
        attachment_count=1
    ))
    assert result["label"] == "Phishing"

def test_security_override_fires():
    """phishing_prob > 0.70 + high-weight signal → Phishing regardless of trust."""
    result = predict(base_features(
        spf_result="fail", dkim_result="none",
        tld_risk_score=3, reply_to_mismatch=True,
        attachment_count=1, first_time_domain=True
    ))
    assert result["label"] == "Phishing"


# ---------------------------------------------------------------------------
# Active signals
# ---------------------------------------------------------------------------

def test_active_signals_spf_dkim_fail():
    result = predict(base_features(spf_result="fail", dkim_result="none"))
    assert "spf_fail_dkim_fail" in result["active_signals"]

def test_active_signals_reply_to_mismatch():
    result = predict(base_features(reply_to_mismatch=True))
    assert "reply_to_mismatch" in result["active_signals"]

def test_active_signals_high_risk_tld():
    result = predict(base_features(tld_risk_score=3))
    assert "high_risk_tld" in result["active_signals"]

def test_active_signals_attachment_first_contact():
    result = predict(base_features(attachment_count=1, first_time_domain=True))
    assert "attachment_first_contact" in result["active_signals"]

def test_no_active_signals_clean_email():
    result = predict(base_features(first_time_domain=False, attachment_count=0))
    assert result["active_signals"] == []
