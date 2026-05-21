"""text_stats.py — uppercase ratio, digit ratio, punctuation density, link density."""
import re
import string

from src.datasets.schema import EmailRecord


def extract(rec: EmailRecord) -> None:
    subject = rec.subject or ""
    body = rec.body_text or ""

    rec.subject_length = len(subject)
    rec.body_length = len(body)

    text = body
    if not text:
        return

    total = len(text)
    letters = sum(c.isalpha() for c in text)

    rec.uppercase_ratio = sum(c.isupper() for c in text) / total if total else 0.0
    rec.digit_ratio = sum(c.isdigit() for c in text) / total if total else 0.0
    rec.punctuation_density = sum(c in string.punctuation for c in text) / total if total else 0.0

    # link density: number of URLs / word count
    word_count = len(text.split())
    link_count = len(re.findall(r'https?://', text))
    rec.link_density = link_count / word_count if word_count else 0.0
