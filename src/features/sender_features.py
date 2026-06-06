"""sender_features.py — display/From mismatch, reply-to mismatch, free-email sender."""
from pathlib import Path

from data.schema import EmailRecord
from src.utils.io import extract_domain, load_lines

_ASSETS = Path(__file__).parents[2] / "data" / "assets"
_FREE_EMAIL = set(load_lines(_ASSETS / "free_email_providers.txt"))


def extract(rec: EmailRecord) -> None:
    sender_domain = extract_domain(rec.sender_address)
    display = rec.sender_display_name.lower()

    # display name / From mismatch: display name contains a domain-like word
    # that differs from the actual sender domain
    display_domain_match = None
    for word in display.replace("@", " ").split():
        if "." in word and len(word) > 4:
            display_domain_match = word.strip(".,<>")
            break
    if display_domain_match and display_domain_match != sender_domain:
        rec.display_from_mismatch = True

    # reply-to mismatch
    if rec.reply_to:
        reply_domain = extract_domain(rec.reply_to)
        if reply_domain and reply_domain != sender_domain:
            rec.reply_to_mismatch = True

    # free-email sender
    rec.free_email_sender = sender_domain in _FREE_EMAIL
