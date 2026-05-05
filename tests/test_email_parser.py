"""
Tests for src/ingestion/email_parser.py

Run:
    python3 -m pytest tests/test_email_parser.py -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.ingestion.email_parser import parse_eml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_eml(
    subject="Test",
    from_addr="sender@example.com",
    reply_to=None,
    auth_results=None,
    body_plain=None,
    body_html=None,
    attachments=0,
) -> bytes:
    """Build a minimal .eml bytes object for testing."""
    lines = [
        f"From: {from_addr}",
        f"To: victim@company.com",
        f"Subject: {subject}",
    ]
    if reply_to:
        lines.append(f"Reply-To: {reply_to}")
    if auth_results:
        lines.append(f"Authentication-Results: mx.test.com; {auth_results}")

    boundary = "testboundary"
    lines += ["MIME-Version: 1.0", f'Content-Type: multipart/mixed; boundary="{boundary}"', ""]

    if body_plain:
        lines += [
            f"--{boundary}",
            "Content-Type: text/plain; charset=utf-8",
            "",
            body_plain,
        ]
    if body_html:
        lines += [
            f"--{boundary}",
            "Content-Type: text/html; charset=utf-8",
            "",
            body_html,
        ]
    for i in range(attachments):
        lines += [
            f"--{boundary}",
            "Content-Type: application/octet-stream",
            f'Content-Disposition: attachment; filename="file{i}.bin"',
            "",
            "data",
        ]
    lines.append(f"--{boundary}--")
    return "\n".join(lines).encode()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

EXPECTED_KEYS = {
    "subject", "body_text", "sender_display_name", "url_token_text",
    "spf_result", "dkim_result", "dmarc_result",
    "url_count", "attachment_count", "reply_to_mismatch",
    "html_text_ratio", "tld_risk_score",
    "sender_seen_before", "first_time_domain",
}

def test_output_keys():
    result = parse_eml(make_eml(body_plain="hello"))
    assert set(result.keys()) == EXPECTED_KEYS


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def test_subject_extracted():
    result = parse_eml(make_eml(subject="Urgent: Verify Now", body_plain="body"))
    assert result["subject"] == "Urgent: Verify Now"

def test_body_plain_extracted():
    result = parse_eml(make_eml(body_plain="Click here to verify your account."))
    assert "verify your account" in result["body_text"]

def test_body_html_fallback():
    """When no plain part, body_text should come from stripped HTML."""
    result = parse_eml(make_eml(body_html="<p>Hello <b>world</b></p>"))
    assert "Hello" in result["body_text"]
    assert "<p>" not in result["body_text"]

def test_sender_display_name():
    result = parse_eml(make_eml(from_addr="Alice <alice@evil.tk>", body_plain="hi"))
    assert result["sender_display_name"] == "Alice <alice@evil.tk>"


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def test_auth_all_pass():
    result = parse_eml(make_eml(
        auth_results="spf=pass; dkim=pass; dmarc=pass",
        body_plain="legit email"
    ))
    assert result["spf_result"] == "pass"
    assert result["dkim_result"] == "pass"
    assert result["dmarc_result"] == "pass"

def test_auth_all_fail():
    result = parse_eml(make_eml(
        auth_results="spf=fail; dkim=none; dmarc=fail",
        body_plain="phishing email"
    ))
    assert result["spf_result"] == "fail"
    assert result["dkim_result"] == "none"
    assert result["dmarc_result"] == "fail"

def test_auth_missing_defaults_to_none():
    """No Authentication-Results header → all default to 'none'."""
    result = parse_eml(make_eml(body_plain="no auth headers"))
    assert result["spf_result"] == "none"
    assert result["dkim_result"] == "none"
    assert result["dmarc_result"] == "none"


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------

def test_url_count():
    body = "Visit http://evil.xyz/login and http://another.tk/steal"
    result = parse_eml(make_eml(body_plain=body))
    assert result["url_count"] == 2

def test_url_count_zero():
    result = parse_eml(make_eml(body_plain="No links here at all."))
    assert result["url_count"] == 0

def test_url_token_text_populated():
    body = "Go to http://micros0ft-verify.xyz/login"
    result = parse_eml(make_eml(body_plain=body))
    assert "micros0ft" in result["url_token_text"]
    assert "xyz" in result["url_token_text"]

def test_url_from_html_href():
    html = '<a href="http://phish.tk/steal">Click here</a>'
    result = parse_eml(make_eml(body_html=html))
    assert result["url_count"] >= 1


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

def test_attachment_count():
    result = parse_eml(make_eml(body_plain="see attached", attachments=2))
    assert result["attachment_count"] == 2

def test_no_attachments():
    result = parse_eml(make_eml(body_plain="no attachments"))
    assert result["attachment_count"] == 0


# ---------------------------------------------------------------------------
# Reply-To mismatch
# ---------------------------------------------------------------------------

def test_reply_to_mismatch_true():
    result = parse_eml(make_eml(
        from_addr="support@paypal.com",
        reply_to="attacker@evil.com",
        body_plain="verify"
    ))
    assert result["reply_to_mismatch"] is True

def test_reply_to_mismatch_false_same_domain():
    result = parse_eml(make_eml(
        from_addr="support@paypal.com",
        reply_to="noreply@paypal.com",
        body_plain="verify"
    ))
    assert result["reply_to_mismatch"] is False

def test_reply_to_absent_no_mismatch():
    result = parse_eml(make_eml(from_addr="sender@legit.com", body_plain="hi"))
    assert result["reply_to_mismatch"] is False


# ---------------------------------------------------------------------------
# TLD risk score
# ---------------------------------------------------------------------------

def test_tld_high_risk():
    result = parse_eml(make_eml(from_addr="x@phish.xyz", body_plain="hi"))
    assert result["tld_risk_score"] == 3

def test_tld_low_risk():
    result = parse_eml(make_eml(from_addr="x@legit.com", body_plain="hi"))
    assert result["tld_risk_score"] == 1


# ---------------------------------------------------------------------------
# HTML/text ratio
# ---------------------------------------------------------------------------

def test_html_text_ratio_zero_when_plain_only():
    result = parse_eml(make_eml(body_plain="just plain text"))
    assert result["html_text_ratio"] == 0.0

def test_html_text_ratio_nonzero_with_html():
    result = parse_eml(make_eml(
        body_plain="hi",
        body_html="<html><body>" + "x" * 500 + "</body></html>"
    ))
    assert result["html_text_ratio"] > 0


# ---------------------------------------------------------------------------
# Hardcoded behavioral defaults
# ---------------------------------------------------------------------------

def test_sender_seen_before_always_false():
    result = parse_eml(make_eml(body_plain="hi"))
    assert result["sender_seen_before"] is False

def test_first_time_domain_always_true():
    result = parse_eml(make_eml(body_plain="hi"))
    assert result["first_time_domain"] is True
