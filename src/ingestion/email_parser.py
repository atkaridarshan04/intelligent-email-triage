"""
Ingestion pipeline: .eml bytes → feature dict matching the training schema.

Output keys (matches parquet schema):
    subject, body_text, sender_display_name, url_token_text,
    spf_result, dkim_result, dmarc_result,
    url_count, attachment_count, reply_to_mismatch,
    html_text_ratio, tld_risk_score,
    sender_seen_before, first_time_domain

sender_seen_before  → always False (no historical DB)
first_time_domain   → always True  (no org domain history)
"""

import email
import re
import sys
from email.message import Message
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.utils.tld_lookup import get_tld_score

# Matches http/https URLs
_URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)

# Parses spf/dkim/dmarc results from Authentication-Results header
# e.g. "spf=pass", "dkim=fail", "dmarc=none"
_AUTH_RE = re.compile(r'\b(spf|dkim|dmarc)=(pass|fail|softfail|neutral|none|permerror|temperror)', re.IGNORECASE)


def _get_domain(addr: str) -> str:
    """Extract domain from an email address string like 'Name <user@domain.com>'."""
    match = re.search(r'@([\w.\-]+)', addr or "")
    return match.group(1).lower() if match else ""


def _parse_auth_results(msg: Message) -> dict[str, str]:
    """Parse Authentication-Results headers into {spf, dkim, dmarc} results."""
    results = {"spf": "none", "dkim": "none", "dmarc": "none"}
    for header_val in msg.get_all("Authentication-Results") or []:
        for proto, result in _AUTH_RE.findall(header_val):
            results[proto.lower()] = result.lower()
    return results


def _extract_body(msg: Message) -> tuple[str, str]:
    """
    Walk MIME parts and return (plain_text, html_text).
    Prefers text/plain; falls back to stripped HTML.
    """
    plain, html = "", ""
    for part in msg.walk():
        ct = part.get_content_type()
        if part.get_content_disposition() == "attachment":
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            decoded = payload.decode(charset, errors="replace")
        except Exception:
            continue
        if ct == "text/plain" and not plain:
            plain = decoded
        elif ct == "text/html" and not html:
            html = decoded
    return plain, html


def _strip_html(html: str) -> str:
    """Minimal HTML tag stripper — no external deps."""
    return re.sub(r'<[^>]+>', ' ', html)


def _extract_urls(text: str, html: str) -> list[str]:
    urls = _URL_RE.findall(text) + _URL_RE.findall(html)
    # Also pull href values from HTML
    hrefs = re.findall(r'href=["\']?(https?://[^\s"\'<>]+)', html, re.IGNORECASE)
    return list(set(urls + hrefs))


def _url_token_text(urls: list[str]) -> str:
    """Tokenise URL domains+paths into space-separated tokens for the text encoder."""
    tokens = []
    for url in urls:
        # strip scheme, split on non-alphanumeric
        stripped = re.sub(r'^https?://', '', url)
        tokens.extend(re.split(r'[/\-_.?=&]+', stripped))
    return " ".join(t for t in tokens if t)


def _count_attachments(msg: Message) -> int:
    return sum(
        1 for part in msg.walk()
        if part.get_content_disposition() == "attachment"
    )


def parse_eml(raw: bytes) -> dict[str, Any]:
    """
    Parse raw .eml bytes into a feature dict.

    Args:
        raw: raw bytes of the .eml file

    Returns:
        dict with all 14 feature fields
    """
    msg = email.message_from_bytes(raw)

    # --- Auth ---
    auth = _parse_auth_results(msg)

    # --- Body ---
    plain, html = _extract_body(msg)
    body_text = plain if plain else _strip_html(html)

    # --- URLs ---
    urls = _extract_urls(plain, html)

    # --- HTML/text ratio ---
    html_len = len(html.strip())
    text_len = len(plain.strip()) or 1  # avoid div/0
    html_text_ratio = round(html_len / text_len, 3)

    # --- Sender ---
    from_addr = msg.get("From", "")
    reply_to  = msg.get("Reply-To", "")
    from_domain    = _get_domain(from_addr)
    reply_domain   = _get_domain(reply_to)
    reply_to_mismatch = bool(reply_domain and reply_domain != from_domain)

    return {
        "subject":             msg.get("Subject", ""),
        "body_text":           body_text.strip(),
        "sender_display_name": from_addr,
        "url_token_text":      _url_token_text(urls),
        "spf_result":          auth["spf"],
        "dkim_result":         auth["dkim"],
        "dmarc_result":        auth["dmarc"],
        "url_count":           len(urls),
        "attachment_count":    _count_attachments(msg),
        "reply_to_mismatch":   reply_to_mismatch,
        "html_text_ratio":     html_text_ratio,
        "tld_risk_score":      get_tld_score(from_domain),
        "sender_seen_before":  False,
        "first_time_domain":   True,
    }
