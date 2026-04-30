"""
Parse CEAS_08.csv, SpamAssasin.csv, Nazario.csv into shared schema JSONL.

CEAS_08:      label=1 → spam,     label=0 → discard
SpamAssasin:  label=1 → spam,     label=0 → discard
Nazario:      label=1 → phishing  (all rows)
"""

import json
import re
import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent.parent.parent / "data"
OUT = {
    "spam":     BASE / "parsed/csv_spam.jsonl",
    "phishing": BASE / "parsed/csv_phishing.jsonl",
}

URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)

SOURCES = [
    (BASE / "CEAS_08.csv",      "ceas08",       "spam",     1),
    (BASE / "SpamAssasin.csv",  "spamassassin", "spam",     1),
    (BASE / "Nazario.csv",      "nazario",      "phishing", 1),
]


def to_record(row, label, source):
    subject = str(row.get("subject", "") or "")
    body    = str(row.get("body", "") or "")
    sender  = str(row.get("sender", "") or "")
    date    = str(row.get("date", "") or "")
    urls_raw = str(row.get("urls", "") or "")

    # urls column may be a stringified list or plain URLs
    urls = URL_RE.findall(urls_raw) or URL_RE.findall(body)

    # Era bucket for domain_age_reliable
    year = 0
    m = re.search(r'\b(20\d{2})\b', date)
    if m:
        year = int(m.group(1))
    domain_age_reliable = year >= 2018

    return {
        "source": source,
        "label": label,
        "subject": subject,
        "body_text": body[:5000],
        "sender_display_name": sender,
        "headers": {"date": date, "reply_to": "", "received_spf": "none",
                    "authentication_results": "", "sending_ip": ""},
        "urls": urls[:50],
        "attachments": [{"count": 0, "mime_type": "", "filename": ""}],
        "spf_result": "none",
        "dkim_result": "none",
        "dmarc_result": "none",
        "url_count": len(urls),
        "attachment_count": 0,
        "reply_to_mismatch": False,
        "html_text_ratio": 0.0,
        "augmented": False,
        "domain_age_reliable": domain_age_reliable,
    }


def main():
    for path in OUT.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")

    handles = {k: open(v, "a") for k, v in OUT.items()}
    counts = {}

    for csv_path, source, label, spam_val in SOURCES:
        df = pd.read_csv(csv_path, on_bad_lines="skip")
        # filter to target label value
        if "label" in df.columns:
            df = df[df["label"] == spam_val]
        n = 0
        for _, row in df.iterrows():
            rec = to_record(row, label, source)
            handles[label].write(json.dumps(rec) + "\n")
            n += 1
        counts[f"{source}({label})"] = n
        print(f"{csv_path.name}: {n} {label} rows")

    for h in handles.values():
        h.close()

    print(f"\nDone.")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print(f"Spam    → {OUT['spam']}")
    print(f"Phishing → {OUT['phishing']}")


if __name__ == "__main__":
    main()
