"""
Parse TREC 2007 corpus into shared schema JSONL.
Output: data/parsed/trec07_spam.jsonl (spam only — ham is discarded)
"""

import email
import json
import re
import os
from email import policy
from pathlib import Path
from html.parser import HTMLParser

DATA_DIR = Path(__file__).parent / "data/trec07p"
INDEX_FILE = DATA_DIR / "full/index"
OUT_FILE = Path(__file__).parent / "data/parsed/trec07_spam.jsonl"
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return " ".join(self.parts)


def extract_body(msg):
    """Return (body_text, html_len, text_len) from email message."""
    text_parts, html_parts = [], []
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                try:
                    text_parts.append(part.get_payload(decode=True).decode("utf-8", errors="replace"))
                except Exception:
                    pass
            elif ct == "text/html":
                try:
                    html_parts.append(part.get_payload(decode=True).decode("utf-8", errors="replace"))
                except Exception:
                    pass
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            raw = payload.decode("utf-8", errors="replace")
            if msg.get_content_type() == "text/html":
                html_parts.append(raw)
            else:
                text_parts.append(raw)

    html_text = ""
    for h in html_parts:
        p = HTMLTextExtractor()
        p.feed(h)
        html_text += p.get_text()

    body_text = " ".join(text_parts) or html_text
    return body_text.strip(), sum(len(h) for h in html_parts), sum(len(t) for t in text_parts)


def extract_urls(msg):
    urls = set()
    if msg.is_multipart():
        for part in msg.walk():
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    urls.update(URL_RE.findall(payload.decode("utf-8", errors="replace")))
            except Exception:
                pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                urls.update(URL_RE.findall(payload.decode("utf-8", errors="replace")))
        except Exception:
            pass
    return list(urls)


def get_auth_header(msg, header_name, default="none"):
    val = str(msg.get(header_name, "") or "")
    if not val:
        return default
    val = val.lower()
    for result in ("pass", "fail", "softfail", "neutral", "none", "temperror", "permerror"):
        if result in val:
            return result
    return default


def parse_email_from_bytes(raw, label, source):
    try:
        msg = email.message_from_bytes(raw, policy=policy.compat32)
    except Exception:
        return None
    return _parse_msg(msg, label, source)


def parse_email(filepath, label):
    try:
        with open(filepath, "rb") as f:
            raw = f.read()
    except OSError:
        return None
    return parse_email_from_bytes(raw, label, "trec07")


def _parse_msg(msg, label, source):

    def h(key, default=""):
        val = msg.get(key, default)
        return str(val) if val else default

    subject = h("Subject")
    sender = h("From")
    date = h("Date")
    reply_to = h("Reply-To")

    body_text, html_len, text_len = extract_body(msg)
    urls = extract_urls(msg)

    # Auth headers
    spf = get_auth_header(msg, "Received-SPF")
    auth_results = str(msg.get("Authentication-Results", "") or "")
    dkim = "none"
    dmarc = "none"
    if "dkim=" in auth_results.lower():
        for r in ("pass", "fail", "none", "policy", "neutral", "temperror", "permerror"):
            if f"dkim={r}" in auth_results.lower():
                dkim = r
                break
    if "dmarc=" in auth_results.lower():
        for r in ("pass", "fail", "bestguesspass", "none"):
            if f"dmarc={r}" in auth_results.lower():
                dmarc = r
                break

    # Reply-to mismatch
    from_domain = re.search(r'@([\w.\-]+)', sender)
    reply_domain = re.search(r'@([\w.\-]+)', reply_to)
    reply_to_mismatch = bool(
        from_domain and reply_domain and
        from_domain.group(1).lower() != reply_domain.group(1).lower()
    )

    # Attachments
    attachment_count = 0
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            attachment_count += 1

    html_text_ratio = round(html_len / max(text_len, 1), 3) if (html_len + text_len) > 0 else 0.0

    # Sending IP from first Received header
    received = str(msg.get("Received", "") or "")
    ip_match = re.search(r'\[(\d{1,3}(?:\.\d{1,3}){3})\]', received)
    sending_ip = ip_match.group(1) if ip_match else ""

    return {
        "source": source,
        "label": "spam",
        "subject": subject,
        "body_text": body_text[:5000],  # cap to avoid huge rows
        "sender_display_name": sender,
        "headers": {
            "date": date,
            "reply_to": reply_to,
            "received_spf": str(msg.get("Received-SPF", "none") or "none"),
            "authentication_results": auth_results[:500],
            "sending_ip": sending_ip,
        },
        "urls": urls[:50],
        "attachments": [{"count": attachment_count, "mime_type": "", "filename": ""}],
        "spf_result": spf,
        "dkim_result": dkim,
        "dmarc_result": dmarc,
        "url_count": len(urls),
        "attachment_count": attachment_count,
        "reply_to_mismatch": reply_to_mismatch,
        "html_text_ratio": html_text_ratio,
        "augmented": False,
        "domain_age_reliable": False,  # pre-2010 corpus
    }


def main():
    # Read index: only keep spam
    spam_files = []
    with open(INDEX_FILE) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2 and parts[0] == "spam":
                # index entries are like: spam ../data/inmail.N
                # resolve relative to the trec07p root dir
                filename = Path(parts[1]).name  # just "inmail.N"
                filepath = DATA_DIR / "data" / filename
                spam_files.append(filepath)

    print(f"Spam emails to parse: {len(spam_files)}")

    written = 0
    errors = 0
    with open(OUT_FILE, "w") as out:
        for i, fp in enumerate(spam_files):
            record = parse_email(fp, "spam")            
            if record is None:
                errors += 1
                continue
            out.write(json.dumps(record) + "\n")
            written += 1
            if (i + 1) % 5000 == 0:
                print(f"  {i+1}/{len(spam_files)} processed...")

    print(f"Done. Written: {written}, Errors: {errors}")
    print(f"Output: {OUT_FILE}")


if __name__ == "__main__":
    main()
