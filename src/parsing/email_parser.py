"""
email_parser.py — Parses raw emails from .eml, CSV, or JSON into EmailRecord.

Supported source formats:
  - .eml  (raw MIME)
  - .csv  (subject, body, label columns — SpamAssassin, TREC, CEAS, Kaggle variants)
  - .json (Nazario, IWSPA-AP, synthetic)
"""
import csv
import email
import json
import re
from email import policy
from pathlib import Path
from typing import Iterator

from src.datasets.schema import AttachmentInfo, EmailRecord
from src.utils.io import email_id


# ---------------------------------------------------------------------------
# .eml parser
# ---------------------------------------------------------------------------

def _parse_eml(path: Path) -> EmailRecord:
    raw = path.read_bytes()
    msg = email.message_from_bytes(raw, policy=policy.default)

    subject = str(msg.get("Subject", ""))
    sender_address = str(msg.get("From", ""))
    reply_to = str(msg.get("Reply-To", ""))
    headers = dict(msg.items())

    # Extract display name vs address
    display_name = ""
    addr_match = re.match(r'^"?([^"<]+)"?\s*<([^>]+)>', sender_address)
    if addr_match:
        display_name = addr_match.group(1).strip()
        sender_address = addr_match.group(2).strip()

    body_text, body_html, urls, attachments = "", "", [], []

    for part in msg.walk():
        ct = part.get_content_type()
        cd = str(part.get("Content-Disposition", ""))
        if "attachment" in cd:
            attachments.append(AttachmentInfo(
                filename=part.get_filename("") or "",
                mime_type=ct,
            ))
        elif ct == "text/plain" and not body_text:
            body_text = part.get_content() or ""
        elif ct == "text/html" and not body_html:
            body_html = part.get_content() or ""

    # Extract URLs from body
    urls = re.findall(r'https?://[^\s<>"\']+', body_text + body_html)

    rec = EmailRecord(
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        sender_display_name=display_name,
        sender_address=sender_address,
        reply_to=reply_to,
        headers=headers,
        urls=urls,
        attachments=attachments,
    )
    rec.id = email_id(rec.subject, rec.body_text)
    return rec


# ---------------------------------------------------------------------------
# CSV parser  (handles SpamAssassin, TREC, CEAS, Kaggle layout variants)
# ---------------------------------------------------------------------------

# Column name aliases → canonical field
_CSV_SUBJECT_COLS = {"subject", "Subject", "SUBJECT"}
_CSV_BODY_COLS = {"body", "Body", "BODY", "text", "Text", "message", "Message", "email_text"}
_CSV_LABEL_COLS = {"label", "Label", "LABEL", "class", "Class", "spam", "category"}
_CSV_SENDER_COLS = {"from", "From", "FROM", "sender", "Sender"}
_CSV_REPLYTO_COLS = {"reply-to", "Reply-To", "replyto"}


def _find_col(headers: list[str], candidates: set[str]) -> str | None:
    for h in headers:
        if h in candidates:
            return h
    return None


def parse_csv(path: Path, source: str, default_label: str = "", max_rows: int = 0) -> Iterator[EmailRecord]:
    with open(path, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []

        col_subject = _find_col(cols, _CSV_SUBJECT_COLS)
        col_body = _find_col(cols, _CSV_BODY_COLS)
        col_label = _find_col(cols, _CSV_LABEL_COLS)
        col_sender = _find_col(cols, _CSV_SENDER_COLS)
        col_replyto = _find_col(cols, _CSV_REPLYTO_COLS)

        for i, row in enumerate(reader):
            if max_rows and i >= max_rows:
                break
            subject = row.get(col_subject, "") if col_subject else ""
            body_text = row.get(col_body, "") if col_body else ""
            raw_label = row.get(col_label, default_label) if col_label else default_label
            sender_address = row.get(col_sender, "") if col_sender else ""
            reply_to = row.get(col_replyto, "") if col_replyto else ""

            urls = re.findall(r'https?://[^\s<>"\']+', body_text)

            rec = EmailRecord(
                subject=subject,
                body_text=body_text,
                sender_address=sender_address,
                reply_to=reply_to,
                urls=urls,
                label=_normalize_label(raw_label),
                source=source,
            )
            rec.id = email_id(rec.subject, rec.body_text)
            yield rec


# ---------------------------------------------------------------------------
# JSON parser  (Nazario, IWSPA-AP, synthetic)
# ---------------------------------------------------------------------------

def parse_json(path: Path, source: str) -> Iterator[EmailRecord]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]

    for item in data:
        rec = EmailRecord(
            subject=item.get("subject", ""),
            body_text=item.get("body_text", item.get("body", "")),
            body_html=item.get("body_html", ""),
            sender_display_name=item.get("sender_display_name", ""),
            sender_address=item.get("sender_address", item.get("from", "")),
            reply_to=item.get("reply_to", ""),
            headers=item.get("headers", {}),
            urls=item.get("urls", []),
            attachments=[
                AttachmentInfo(**a) for a in item.get("attachments", [])
            ],
            label=_normalize_label(item.get("label", "")),
            source=source,
            era_bucket=item.get("era_bucket", ""),
            subtype=item.get("subtype", ""),
            augmented=item.get("augmented", False),
        )
        rec.id = email_id(rec.subject, rec.body_text)
        yield rec


# ---------------------------------------------------------------------------
# Label normalizer
# ---------------------------------------------------------------------------

# Kaggle CSVs: 0=spam/ham, 1=phishing
# TREC index: "spam"=spam, "ham"=not-spam (we skip ham)
_SPAM_LABELS = {"spam", "0", "junk", "bulk", "unsolicited", "ham"}
_PHISHING_LABELS = {"phishing", "phish", "malicious", "fraud", "1"}


def _normalize_label(raw: str) -> str:
    v = str(raw).strip().lower()
    if v in _SPAM_LABELS:
        return "spam"
    if v in _PHISHING_LABELS:
        return "phishing"
    return ""  # unknown — caller decides whether to drop or assign


# ---------------------------------------------------------------------------
# TREC 2007 loader — reads full/index then loads labeled .eml files
# ---------------------------------------------------------------------------

def parse_trec(trec_root: Path, source: str = "trec", max_rows: int = 0) -> Iterator[EmailRecord]:
    """
    Load TREC 2007 corpus.
    Expects: trec_root/full/index  and  trec_root/data/inmail.*
    Index format: '<spam|ham> ../data/inmail.N'
    We load spam only (ham is legitimate email, not relevant to our task).
    """
    index_file = trec_root / "full" / "index"
    if not index_file.exists():
        return

    count = 0
    with open(index_file, encoding="utf-8", errors="replace") as f:
        for line in f:
            if max_rows and count >= max_rows:
                break
            parts = line.strip().split()
            if len(parts) != 2:
                continue
            label_str, rel_path = parts
            if label_str not in ("spam", "ham"):
                continue
            if label_str == "ham":
                continue  # ham = legitimate email — skip, do not mislabel as spam

            email_path = (trec_root / rel_path.lstrip("./")).resolve()
            if not email_path.exists():
                # try relative to index file's parent
                email_path = (index_file.parent / rel_path).resolve()
            if not email_path.exists():
                continue

            try:
                rec = _parse_eml(email_path)
                rec.source = source
                rec.label = _normalize_label(label_str)
                rec.era_bucket = "legacy"  # TREC 2007
                yield rec
                count += 1
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Directory loader — auto-detects format
# ---------------------------------------------------------------------------

def load_directory(directory: Path, source: str, default_label: str = "", max_rows: int = 0) -> Iterator[EmailRecord]:
    """Recursively load all email files from a directory.
    Handles .eml files and extensionless raw email files (e.g. SpamAssassin corpus).
    """
    count = 0
    for path in sorted(directory.rglob("*")):
        if max_rows and count >= max_rows:
            break
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        # Skip archives and known non-email files
        if suffix in (".bz2", ".gz", ".zip", ".tar", ".json", ".csv", ".txt", ".md", ".py", ".ipynb"):
            continue
        try:
            rec = _parse_eml(path)
            rec.source = source
            rec.label = _normalize_label(default_label)
            yield rec
            count += 1
        except Exception:
            pass
