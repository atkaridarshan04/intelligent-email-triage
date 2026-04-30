"""
Phase 7.3 — URL reputation lookup via OpenPhish.

Downloads the OpenPhish feed (free, no API key required) and checks
every URL in shared/urls.txt against it.

OpenPhish feed: https://openphish.com/feed.txt
  - Plain text, one URL per line, updated every 12 hours
  - No registration required

Writes cache/phishtank/url_hits.json
  { "url": bool, ... }  — True = confirmed phishing hit

Usage:
    python src/datasets/phishtank_lookup.py
"""

import json
import urllib.request
from pathlib import Path

URLS_FILE  = Path("shared/urls.txt")
CACHE_DIR  = Path("cache/phishtank")
HITS_FILE  = CACHE_DIR / "url_hits.json"

OPENPHISH_URL = "https://openphish.com/feed.txt"


def download_feed() -> set[str]:
    """Download OpenPhish feed and return set of phishing URLs."""
    print(f"Downloading OpenPhish feed...")
    req = urllib.request.Request(
        OPENPHISH_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        content = resp.read().decode("utf-8", errors="replace")

    urls = {line.strip() for line in content.splitlines() if line.strip()}
    print(f"  Loaded {len(urls):,} phishing URLs from OpenPhish")
    return urls


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    urls = [u.strip() for u in URLS_FILE.read_text().splitlines() if u.strip()]
    print(f"URLs to check: {len(urls):,}")

    # Load existing hits if resuming
    existing = {}
    if HITS_FILE.exists():
        existing = json.loads(HITS_FILE.read_text())
        print(f"  Loaded {len(existing):,} cached results")

    phishing_set = download_feed()

    hits = dict(existing)
    new_checked = 0
    for url in urls:
        if url in hits:
            continue
        hits[url] = url in phishing_set
        new_checked += 1

    HITS_FILE.write_text(json.dumps(hits), encoding="utf-8")

    total_hits = sum(1 for v in hits.values() if v)
    print(f"\nNew checked  : {new_checked:,}")
    print(f"Total URLs   : {len(hits):,}")
    print(f"Phishing hits: {total_hits:,} ({total_hits/max(len(hits),1):.1%})")
    print(f"Output: {HITS_FILE}")


if __name__ == "__main__":
    main()
