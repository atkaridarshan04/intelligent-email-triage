"""
Phase 2.4 — Compute Enron behavioral history from the full parsed corpus.

Reads  data/interim/enron_parsed/enron_parsed.jsonl
Writes data/interim/enron_behavioral_history.json

For each email in the labeled Junk set, computes:
  sender_seen_before      : bool  — sender emailed this recipient before this email
  communication_frequency : int   — total prior emails from sender to recipient
  first_time_domain       : bool  — first email from sender's domain to this recipient
  send_hour_deviation     : float — abs(email_hour - sender's median send hour)

History is computed strictly from emails dated BEFORE the target email (no leakage).
All results keyed by the email's "file" field for joining back to labeled set.

Usage:
    python src/compute_behavioral_history.py
"""

import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

IN_FILE  = Path("data/interim/enron_parsed/enron_parsed.jsonl")
OUT_FILE = Path("data/interim/enron_behavioral_history.json")
LABELED  = Path("data/interim/junk_candidates/junk_labeled.jsonl")


def parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        # normalize to UTC-naive for comparison
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def main():
    # --- Pass 1: load full corpus into memory (file, from, to_domain, date, hour) ---
    print("Pass 1: loading corpus...")
    corpus = []  # list of (file, from_addr, from_domain, to_addr, date, hour)

    with open(IN_FILE, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            from_addr = rec["from_address"]
            from_domain = from_addr.split("@")[-1] if "@" in from_addr else ""
            to_addr = rec["to_address"].strip().lower()
            dt = parse_date(rec["date"])
            hour = dt.hour if dt else None
            corpus.append((rec["file"], from_addr, from_domain, to_addr, dt, hour))

    print(f"  Loaded {len(corpus):,} emails")

    # --- Load target files (only need behavioral history for labeled Junk) ---
    target_files = set()
    with open(LABELED, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            target_files.add(rec["file"])

    print(f"  Target emails needing history: {len(target_files):,}")

    # --- Sort corpus by date for chronological processing ---
    # Emails with no date go to end (treated as latest)
    corpus.sort(key=lambda x: x[4] or datetime.max)

    # --- Pass 2: build running history, record features for target emails ---
    print("Pass 2: computing behavioral features...")

    # Running state
    # pair_count[(from_addr, to_addr)] = count of prior emails
    # domain_pair_count[(from_domain, to_addr)] = count of prior emails from domain
    # sender_hours[from_addr] = list of prior send hours
    pair_count: dict[tuple, int] = defaultdict(int)
    domain_pair_count: dict[tuple, int] = defaultdict(int)
    sender_hours: dict[str, list[int]] = defaultdict(list)

    results = {}

    for file, from_addr, from_domain, to_addr, dt, hour in corpus:
        if file in target_files:
            prior_pair = pair_count[(from_addr, to_addr)]
            prior_domain = domain_pair_count[(from_domain, to_addr)]
            prior_hours = sender_hours[from_addr]

            if prior_hours:
                median_hour = statistics.median(prior_hours)
                deviation = abs((hour or 12) - median_hour)
            else:
                deviation = 0.0  # no history → no deviation computable

            results[file] = {
                "sender_seen_before": prior_pair > 0,
                "communication_frequency": prior_pair,
                "first_time_domain": prior_domain == 0,
                "send_hour_deviation": round(deviation, 2),
            }

        # Update running state AFTER recording (strict "before this email" semantics)
        pair_count[(from_addr, to_addr)] += 1
        if from_domain:
            domain_pair_count[(from_domain, to_addr)] += 1
        if hour is not None:
            sender_hours[from_addr].append(hour)

    print(f"  Computed history for {len(results):,} target emails")

    # --- Write output ---
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f)

    print(f"Output: {OUT_FILE}")

    # --- Quick sanity stats ---
    seen_before = sum(1 for v in results.values() if v["sender_seen_before"])
    first_domain = sum(1 for v in results.values() if v["first_time_domain"])
    print(f"\nSanity check:")
    print(f"  sender_seen_before=True : {seen_before:,} / {len(results):,}")
    print(f"  first_time_domain=True  : {first_domain:,} / {len(results):,}")


if __name__ == "__main__":
    main()
