import hashlib
import json
import re
from pathlib import Path


def email_id(subject: str, body_text: str) -> str:
    """Canonical deduplication hash: sha256(subject + body_text[:500])."""
    key = (subject + body_text[:500]).encode("utf-8", errors="replace")
    return hashlib.sha256(key).hexdigest()


def load_json(path: Path) -> dict | list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_lines(path: Path) -> list[str]:
    """Load a text file as a list of non-empty, non-comment lines."""
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def extract_domain(address: str) -> str:
    """Extract domain from an email address or URL."""
    address = address.strip().lower()
    if "@" in address and "/" not in address:
        return address.split("@")[-1]
    match = re.search(r"https?://([^/?\s]+)", address)
    if match:
        return match.group(1).split(":")[0]
    return address


def era_bucket(year: int | None) -> str:
    if year is None:
        return "unknown"
    if year < 2010:
        return "legacy"
    if year < 2018:
        return "mid"
    return "recent"
