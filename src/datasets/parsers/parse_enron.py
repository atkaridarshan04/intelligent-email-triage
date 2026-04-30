"""
Phase 2.2 — Parse Enron CSV into structured JSONL.

Reads data/raw/enron/emails.csv, parses each raw message,
and writes data/interim/enron_parsed/enron_parsed.jsonl.

One JSON object per line. Missing auth headers → "none".

Usage:
    python src/parse_enron.py
"""

import csv
import json
import re
import email
from email import policy
from email.utils import parseaddr, getaddresses
from pathlib import Path
from urllib.parse import urlparse
import html
from bs4 import BeautifulSoup

RAW_CSV   = Path("data/raw/enron/emails.csv")
OUT_FILE  = Path("data/interim/enron_parsed/enron_parsed.jsonl")
URL_RE    = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)


def extract_urls(text: str) -> list[str]:
    return URL_RE.findall(text or "")


def extract_urls_from_html(html_content: str) -> list[str]:
    soup = BeautifulSoup(html_content, "html.parser")
    return [a["href"] for a in soup.find_all("a", href=True)
            if a["href"].startswith("http")]


def get_body_and_ratio(msg: email.message.Message) -> tuple[str, float]:
    """Returns (plain_text_body, html_to_text_ratio)."""
    plain, html_body = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain" and not plain:
                plain = part.get_payload(decode=True).decode(errors="replace")
            elif ct == "text/html" and not html_body:
                html_body = part.get_payload(decode=True).decode(errors="replace")
    else:
        ct = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if payload:
            decoded = payload.decode(errors="replace")
            if ct == "text/html":
                html_body = decoded
                plain = BeautifulSoup(decoded, "html.parser").get_text()
            else:
                plain = decoded

    ratio = len(html_body) / max(len(plain), 1) if html_body else 0.0
    return plain.strip(), round(ratio, 4)


def get_attachments(msg: email.message.Message) -> list[dict]:
    attachments = []
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            attachments.append({
                "mime_type": part.get_content_type(),
                "filename": part.get_filename() or ""
            })
    return attachments


def parse_auth_results(headers: dict) -> tuple[str, str, str]:
    """Extract SPF, DKIM, DMARC from Authentication-Results or dedicated headers."""
    auth = headers.get("Authentication-Results", "").lower()
    spf_header = headers.get("Received-SPF", "").lower()

    # SPF
    if spf_header:
        for val in ("pass", "fail", "softfail", "neutral", "none"):
            if spf_header.startswith(val):
                spf = val
                break
        else:
            spf = "none"
    elif "spf=pass" in auth:
        spf = "pass"
    elif "spf=fail" in auth:
        spf = "fail"
    elif "spf=softfail" in auth:
        spf = "softfail"
    else:
        spf = "none"

    # DKIM
    if "dkim=pass" in auth:
        dkim = "pass"
    elif "dkim=fail" in auth:
        dkim = "fail"
    else:
        dkim = "none"

    # DMARC
    if "dmarc=pass" in auth:
        dmarc = "pass"
    elif "dmarc=fail" in auth:
        dmarc = "fail"
    else:
        dmarc = "none"

    return spf, dkim, dmarc


def parse_message(file_path: str, raw: str) -> dict | None:
    try:
        msg = email.message_from_string(raw, policy=policy.compat32)
    except Exception:
        return None

    headers = dict(msg.items())

    from_raw = msg.get("From", "")
    display_name, from_addr = parseaddr(from_raw)

    reply_to_raw = msg.get("Reply-To", "")
    _, reply_to_addr = parseaddr(reply_to_raw)

    from_domain   = from_addr.split("@")[-1].lower() if "@" in from_addr else ""
    reply_domain  = reply_to_addr.split("@")[-1].lower() if "@" in reply_to_addr else ""
    reply_mismatch = bool(reply_to_addr and reply_domain != from_domain)

    body, html_ratio = get_body_and_ratio(msg)
    urls = extract_urls(body)
    if not urls:
        # also try HTML part
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                raw_html = part.get_payload(decode=True)
                if raw_html:
                    urls = extract_urls_from_html(raw_html.decode(errors="replace"))
                break

    spf, dkim, dmarc = parse_auth_results(headers)

    date_str = msg.get("Date", "")

    return {
        "file": file_path,
        "subject": msg.get("Subject", "").strip(),
        "body_text": body,
        "sender_display_name": display_name.strip(),
        "from_address": from_addr.lower().strip(),
        "to_address": msg.get("To", "").strip(),
        "date": date_str,
        "headers": {k: v for k, v in headers.items()},
        "urls": urls,
        "attachments": get_attachments(msg),
        "spf_result": spf,
        "dkim_result": dkim,
        "dmarc_result": dmarc,
        "reply_to_mismatch": reply_mismatch,
        "html_text_ratio": html_ratio,
    }


def main():
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    csv.field_size_limit(10_000_000)  # 10MB — Enron has large email bodies

    # Resume: count already-written lines to skip that many CSV rows
    already_done = 0
    if OUT_FILE.exists():
        with open(OUT_FILE, "rb") as f:
            already_done = sum(1 for _ in f)
        print(f"Resuming from row {already_done:,} (output file already has {already_done:,} lines)")

    parsed, skipped = 0, 0

    with open(RAW_CSV, newline="", encoding="utf-8", errors="replace") as csvf, \
         open(OUT_FILE, "a", encoding="utf-8") as outf:

        reader = csv.DictReader(csvf)
        for i, row in enumerate(reader):
            if i < already_done:
                continue
            result = parse_message(row["file"], row["message"])
            if result is None:
                skipped += 1
                continue
            outf.write(json.dumps(result) + "\n")
            parsed += 1
            if parsed % 50_000 == 0:
                print(f"  parsed {already_done + parsed:,} emails total...")

    print(f"\nDone. New: {parsed:,}  Skipped: {skipped:,}  Total in file: {already_done + parsed:,}")
    print(f"Output: {OUT_FILE}")


if __name__ == "__main__":
    main()
