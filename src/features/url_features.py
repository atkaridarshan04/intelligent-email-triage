"""url_features.py — URL count, TLD risk, entropy, typosquatting, IP literal, shorteners."""
import math
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from data.schema import EmailRecord
from src.utils.io import load_json, load_lines

_ASSETS = Path(__file__).parents[2] / "data" / "assets"
_TLD_TABLE = load_json(_ASSETS / "tld_risk_table.json")
_SHORTENERS = set(load_lines(_ASSETS / "url_shorteners.txt"))
_BRAND_DOMAINS = load_lines(_ASSETS / "brand_domains.txt")

# Flatten high+medium risk TLDs into a set for quick lookup
_SUSPICIOUS_TLDS: set[str] = set(
    _TLD_TABLE["high"]["tlds"] + _TLD_TABLE["medium"]["tlds"]
)

_IP_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


def _domain_entropy(domain: str) -> float:
    """Shannon entropy of characters in the domain label (excluding TLD)."""
    label = domain.split(".")[0] if "." in domain else domain
    if not label:
        return 0.0
    counts = Counter(label)
    total = len(label)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


def _normalize_unicode(s: str) -> str:
    """Replace common Cyrillic/homoglyph lookalikes with ASCII equivalents."""
    replacements = {"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x"}
    return "".join(replacements.get(ch, ch) for ch in s.lower())


def extract(rec: EmailRecord) -> None:
    urls = rec.urls
    rec.url_count = len(urls)

    domains = set()
    for url in urls:
        try:
            host = urlparse(url).hostname or ""
        except Exception:
            host = ""
        if not host:
            continue
        host = host.lower()
        domains.add(host)

        # IP literal
        if _IP_RE.match(host):
            rec.ip_literal_url = True

        # Shortened URL
        if host in _SHORTENERS or any(host.endswith("." + s) for s in _SHORTENERS):
            rec.shortened_url_present = True

        # Suspicious TLD
        for tld in _SUSPICIOUS_TLDS:
            if host.endswith(tld):
                rec.suspicious_tld_present = True
                break

        # Typosquatting: edit distance ≤ 2 against brand domains
        norm_host = _normalize_unicode(host.split(":")[0])
        # strip subdomains — compare registered domain only
        parts = norm_host.split(".")
        registered = ".".join(parts[-2:]) if len(parts) >= 2 else norm_host
        for brand in _BRAND_DOMAINS:
            if registered == brand:
                break  # exact match — not typosquatting
            if _levenshtein(registered, brand) <= 2:
                rec.typosquatting_detected = True
                break
            # subdomain abuse: brand appears as subdomain of attacker domain
            if norm_host != brand and norm_host.startswith(brand + "."):
                rec.typosquatting_detected = True
                break

    rec.domain_count = len(domains)

    # URL entropy: average over all domains
    if domains:
        rec.url_entropy = sum(_domain_entropy(d) for d in domains) / len(domains)
