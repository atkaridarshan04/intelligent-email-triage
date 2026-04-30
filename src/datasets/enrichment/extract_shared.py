"""
Phase 6 — Extract shared files for Track B

Reads spam_deduped.jsonl and phishing_deduped.jsonl (all parsed corpora).
Extracts and writes:
  shared/domains.txt  — unique sender domains
  shared/ips.txt      — unique sending IPs (from Received headers)
  shared/urls.txt     — unique URLs from email bodies

This unblocks Track B's WHOIS / Spamhaus / PhishTank lookups.
"""

import json
import re
from pathlib import Path

BASE   = Path(__file__).parent.parent.parent / "data"
SHARED = Path(__file__).parent.parent.parent / "shared"

INPUTS = [
    BASE / "parsed/spam_deduped.jsonl",
    BASE / "parsed/phishing_deduped.jsonl",
]

DOMAIN_RE = re.compile(r'@([\w.\-]+)', re.IGNORECASE)
IP_RE     = re.compile(r'\b(\d{1,3}(?:\.\d{1,3}){3})\b')
URL_RE    = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)


def extract_domain(sender: str) -> str | None:
    m = DOMAIN_RE.search(sender)
    if m:
        return m.group(1).lower().strip(".")
    return None


def extract_ip(headers: dict) -> str | None:
    ip_str = headers.get("sending_ip", "") or headers.get("received", "")
    m = IP_RE.search(ip_str)
    if m:
        return m.group(1)
    # Also scan authentication_results
    auth = headers.get("authentication_results", "")
    m = IP_RE.search(auth)
    if m:
        return m.group(1)
    return None


def main():
    SHARED.mkdir(parents=True, exist_ok=True)

    domains = set()
    ips     = set()
    urls    = set()

    for path in INPUTS:
        if not path.exists():
            print(f"Missing: {path}")
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)

                # Sender domain
                sender = r.get("sender_display_name", "")
                d = extract_domain(sender)
                if d:
                    domains.add(d)

                # Sending IP from headers
                headers = r.get("headers", {})
                ip = extract_ip(headers)
                if ip:
                    ips.add(ip)

                # URLs from urls field + body scan
                for u in r.get("urls", []):
                    if u:
                        urls.add(u.strip())
                body = r.get("body_text", "")
                for u in URL_RE.findall(body):
                    urls.add(u.strip())

    # Write outputs
    (SHARED / "domains.txt").write_text("\n".join(sorted(domains)) + "\n", encoding="utf-8")
    (SHARED / "ips.txt").write_text("\n".join(sorted(ips)) + "\n", encoding="utf-8")
    (SHARED / "urls.txt").write_text("\n".join(sorted(urls)) + "\n", encoding="utf-8")

    print(f"Domains: {len(domains):,}  → {SHARED / 'domains.txt'}")
    print(f"IPs:     {len(ips):,}  → {SHARED / 'ips.txt'}")
    print(f"URLs:    {len(urls):,}  → {SHARED / 'urls.txt'}")
    print("Track B handoff complete.")


if __name__ == "__main__":
    main()
