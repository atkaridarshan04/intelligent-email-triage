"""brand_features.py — known brand mention detection, sender-brand mismatch."""
from pathlib import Path

from src.datasets.schema import EmailRecord
from src.utils.io import extract_domain, load_lines

_ASSETS = Path(__file__).parents[2] / "data" / "assets"
_BRAND_DOMAINS = load_lines(_ASSETS / "brand_domains.txt")
# Extract just the brand name (first label) for text matching
_BRAND_NAMES = [d.split(".")[0].lower() for d in _BRAND_DOMAINS]


def extract(rec: EmailRecord) -> None:
    text = (rec.subject + " " + rec.body_text).lower()
    sender_domain = extract_domain(rec.sender_address)

    for brand_name, brand_domain in zip(_BRAND_NAMES, _BRAND_DOMAINS):
        if brand_name in text:
            rec.brand_mention = True
            # mismatch: brand mentioned but sender domain doesn't match
            if brand_domain not in sender_domain and sender_domain not in brand_domain:
                rec.sender_brand_mismatch = True
            break  # one brand match is enough to set the flags
