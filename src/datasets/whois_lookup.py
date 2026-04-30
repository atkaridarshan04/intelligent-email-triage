"""
Phase 7.1 — WHOIS lookups for domain age.

Reads  shared/domains.txt
Writes cache/whois/{domain}.json per domain

Result schema:
  { "domain": str, "creation_date": str|null, "domain_age_days": int|null, "error": str|null }

- Skips domains already cached.
- Rate-limited to avoid WHOIS server bans (1s between queries).
- domain_age_reliable=False flag is set at Phase 8 for pre-2010 emails — not here.

Usage:
    python src/datasets/whois_lookup.py
"""

import json
import time
import re
import signal
from datetime import datetime, timezone
from pathlib import Path
import whois

DOMAINS_FILE = Path("shared/domains.txt")
CACHE_DIR    = Path("cache/whois")
RATE_LIMIT   = 0.2   # seconds between queries — WHOIS servers responding fast
WHOIS_TIMEOUT = 15   # seconds per domain before giving up


class TimeoutError(Exception):
    pass


def with_timeout(fn, seconds):
    def handler(signum, frame):
        raise TimeoutError()
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        return fn()
    finally:
        signal.alarm(0)


def safe_date(val) -> str | None:
    """Normalize whois creation_date (may be list or datetime) to ISO string."""
    if val is None:
        return None
    if isinstance(val, list):
        val = val[0]
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def age_days(creation_iso: str | None) -> int | None:
    if not creation_iso:
        return None
    try:
        dt = datetime.fromisoformat(creation_iso.replace("Z", "+00:00"))
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return (datetime.now(timezone.utc).replace(tzinfo=None) - dt).days
    except Exception:
        return None


def safe_filename(domain: str) -> str:
    """Strip characters unsafe for filenames."""
    return re.sub(r'[^\w.\-]', '_', domain)


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    domains = [d.strip() for d in DOMAINS_FILE.read_text().splitlines() if d.strip()]
    total   = len(domains)
    done, skipped, errors = 0, 0, 0

    print(f"Domains to process: {total:,}")

    for i, domain in enumerate(domains):
        cache_file = CACHE_DIR / f"{safe_filename(domain)}.json"
        if cache_file.exists():
            skipped += 1
            continue

        result = {"domain": domain, "creation_date": None, "domain_age_days": None, "error": None}
        try:
            w = with_timeout(lambda: whois.whois(domain), WHOIS_TIMEOUT)
            creation_iso = safe_date(w.creation_date)
            result["creation_date"]  = creation_iso
            result["domain_age_days"] = age_days(creation_iso)
        except Exception as e:
            result["error"] = str(e)[:200]
            errors += 1

        cache_file.write_text(json.dumps(result), encoding="utf-8")
        done += 1

        if done % 500 == 0:
            print(f"  {i+1:,}/{total:,} — done={done:,} skipped={skipped:,} errors={errors:,}")

        time.sleep(RATE_LIMIT)

    print(f"\nDone. Queried={done:,}  Skipped(cached)={skipped:,}  Errors={errors:,}")
    print(f"Cache: {CACHE_DIR}")


if __name__ == "__main__":
    main()
