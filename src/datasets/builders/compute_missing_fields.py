"""
Compute missing fields for spam and phishing records so all three classes
share the same 15-field schema before merging.

Fields added to spam:
  - url_token_text   (from urls list)
  - tld_risk_score   (from sender domain)
  - sender_seen_before = False
  - first_time_domain = True

Fields added to phishing:
  - url_token_text   (from urls list)
  - tld_risk_score   (from sender domain)
  - sender_seen_before = False
  - first_time_domain: fill nulls with True (organic Nazario may be null)
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.utils.tld_lookup import get_tld_score

SENDER_EMAIL_RE = re.compile(r'<([^>]+)>|(\S+@\S+)')

INPUT = {
    "spam":     Path("data/processed/classes/spam_class.jsonl"),
    "phishing": Path("data/processed/classes/phishing_class.jsonl"),
}
OUTPUT = {
    "spam":     Path("data/processed/enriched/spam_class_enriched.jsonl"),
    "phishing": Path("data/processed/enriched/phishing_class_enriched.jsonl"),
}


def extract_sender_domain(sender_display_name: str) -> str:
    m = SENDER_EMAIL_RE.search(sender_display_name or "")
    if m:
        addr = m.group(1) or m.group(2)
        return addr.split("@")[-1].strip(">").lower()
    return ""


def urls_to_token_text(urls) -> str:
    if not urls:
        return ""
    tokens = []
    for url in urls:
        try:
            p = urlparse(url)
            parts = [p.netloc] + [seg for seg in p.path.split("/") if seg]
            tokens.extend(parts)
        except Exception:
            tokens.append(url)
    return " ".join(tokens)


def enrich(row: dict, label: str) -> dict:
    row["url_token_text"] = urls_to_token_text(row.get("urls") or [])
    domain = extract_sender_domain(row.get("sender_display_name", ""))
    row["tld_risk_score"] = get_tld_score(domain)
    row["sender_seen_before"] = False
    if label == "spam":
        row["first_time_domain"] = True
    else:  # phishing — fill nulls only
        if row.get("first_time_domain") is None:
            row["first_time_domain"] = True
    return row


def process(label: str):
    in_path, out_path = INPUT[label], OUTPUT[label]
    count = 0
    with open(in_path) as fin, open(out_path, "w") as fout:
        for line in fin:
            row = json.loads(line)
            fout.write(json.dumps(enrich(row, label)) + "\n")
            count += 1
    print(f"{label}: {count} records written to {out_path}")


if __name__ == "__main__":
    process("spam")
    process("phishing")
