"""
Parse SpamAssassin tar.bz2 files into shared schema JSONL.
Spam tarballs  → data/parsed/spamassassin_spam.jsonl
Hard ham tarballs → data/shared/hard_ham.jsonl  (Track B handoff)
"""

import tarfile
import json
import email
from email import policy
from pathlib import Path
from src.datasets.parsers.parse_trec import parse_email_from_bytes  # reuse parser

BASE = Path(__file__).parent.parent.parent / "data"
OUT_SPAM = BASE / "parsed/spamassassin_spam.jsonl"
OUT_HARD_HAM = BASE / "shared/hard_ham.jsonl"

SPAM_TARBALLS = [
    BASE / "20021010_spam.tar.bz2",
    BASE / "20030228_spam.tar.bz2",
    BASE / "20030228_spam_2.tar.bz2",
    BASE / "20050311_spam_2.tar.bz2",
]

HARD_HAM_TARBALLS = [
    BASE / "20021010_hard_ham.tar.bz2",
    BASE / "20030228_hard_ham.tar.bz2",
]


def parse_tarball(tarball_path, label, source_tag, out_file):
    written = 0
    with tarfile.open(tarball_path, "r:bz2") as tar, open(out_file, "a") as out:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            try:
                raw = tar.extractfile(member).read()
                record = parse_email_from_bytes(raw, label, source_tag)
                if record:
                    out.write(json.dumps(record) + "\n")
                    written += 1
            except Exception:
                pass
    return written


def main():
    OUT_SPAM.parent.mkdir(parents=True, exist_ok=True)
    OUT_HARD_HAM.parent.mkdir(parents=True, exist_ok=True)

    # Clear output files
    OUT_SPAM.write_text("")
    OUT_HARD_HAM.write_text("")

    total_spam = 0
    for tb in SPAM_TARBALLS:
        n = parse_tarball(tb, "spam", "spamassassin", OUT_SPAM)
        print(f"{tb.name}: {n} spam")
        total_spam += n

    total_ham = 0
    for tb in HARD_HAM_TARBALLS:
        n = parse_tarball(tb, "junk", "spamassassin_hard_ham", OUT_HARD_HAM)
        print(f"{tb.name}: {n} hard ham")
        total_ham += n

    print(f"\nDone. Spam: {total_spam} → {OUT_SPAM}")
    print(f"Hard ham: {total_ham} → {OUT_HARD_HAM}")


if __name__ == "__main__":
    main()
