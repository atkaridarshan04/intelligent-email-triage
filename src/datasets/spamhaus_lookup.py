"""
Phase 7.2 — Spamhaus ZEN IP reputation lookups.

Reads  shared/ips.txt
Writes cache/spamhaus/{ip}.json per IP

Result schema:
  { "ip": str, "listed": bool, "error": str|null }

DNS lookup: reverse IP octets + .zen.spamhaus.org
  Result    → listed=True
  NXDOMAIN  → listed=False

- Skips IPs already cached.
- Free for non-commercial use.

Usage:
    python src/datasets/spamhaus_lookup.py
"""

import json
import re
from pathlib import Path
import dns.resolver
import dns.exception

IPS_FILE  = Path("shared/ips.txt")
CACHE_DIR = Path("cache/spamhaus")


def check_ip(ip: str) -> tuple[bool, str | None]:
    """Returns (listed, error)."""
    try:
        reversed_ip = ".".join(reversed(ip.split(".")))
        query = f"{reversed_ip}.zen.spamhaus.org"
        dns.resolver.resolve(query, "A")
        return True, None
    except dns.resolver.NXDOMAIN:
        return False, None
    except Exception as e:
        return False, str(e)[:200]


def safe_filename(ip: str) -> str:
    return ip.replace(".", "_")


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    ips = [ip.strip() for ip in IPS_FILE.read_text().splitlines()
           if ip.strip() and re.match(r'^\d{1,3}(\.\d{1,3}){3}$', ip.strip())]
    total = len(ips)
    done, skipped, errors = 0, 0, 0

    print(f"IPs to process: {total:,}")

    for i, ip in enumerate(ips):
        cache_file = CACHE_DIR / f"{safe_filename(ip)}.json"
        if cache_file.exists():
            skipped += 1
            continue

        listed, error = check_ip(ip)
        result = {"ip": ip, "listed": listed, "error": error}
        cache_file.write_text(json.dumps(result), encoding="utf-8")
        done += 1
        if error:
            errors += 1

        if done % 1000 == 0:
            print(f"  {i+1:,}/{total:,} — done={done:,} skipped={skipped:,} errors={errors:,}")

    print(f"\nDone. Queried={done:,}  Skipped(cached)={skipped:,}  Errors={errors:,}")
    print(f"Cache: {CACHE_DIR}")


if __name__ == "__main__":
    main()
