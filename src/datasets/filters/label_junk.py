"""
Phase 4 — Apply Junk labeling rules to Enron filtered candidates.

Reads  data/interim/junk_candidates/enron_junk_candidates.jsonl
Writes data/interim/junk_candidates/junk_labeled.jsonl

Label as Junk if score >= 2 positive signals AND zero disqualifiers.
Each record gets: label="junk", junk_score (int), matched_signals (list).
"""

import json
import re
from pathlib import Path

IN_FILE  = Path("data/interim/junk_candidates/enron_junk_candidates.jsonl")
OUT_FILE = Path("data/interim/junk_candidates/junk_labeled.jsonl")

# ---------------------------------------------------------------------------
# Disqualifiers — any match → discard entirely
# ---------------------------------------------------------------------------
DISQUALIFIERS = [
    (re.compile(
        r"(verify your (account|identity|email|password)|confirm your (account|password|login)|"
        r"enter your (password|credentials|login)|"
        r"click here to (verify|confirm|restore|reactivate|unlock)|"
        r"your (account|access) (has been|will be) (suspended|locked|disabled|terminated)|"
        r"login to (avoid|prevent|restore)|"
        r"update your (payment|billing|credit card) (info|information|details))",
        re.IGNORECASE,
    ), "credential_request"),

    (re.compile(
        r"(wire transfer|gift card|invoice (payment|attached)|"
        r"urgent (payment|transfer|wire)|bank account (change|update)|"
        r"payroll (redirect|update)|pay (this|the) invoice)",
        re.IGNORECASE,
    ), "financial_fraud"),

    (re.compile(
        r"(dear (ceo|cfo|director|president|executive)|"
        r"on behalf of (the ceo|our ceo|management)|"
        r"impersonat|acting as|posing as)",
        re.IGNORECASE,
    ), "executive_impersonation"),

    (re.compile(
        r"(\.exe|\.bat|\.cmd|\.ps1|\.vbs|\.js attached|"
        r"macro.enabled|enable macros|password.protected (zip|rar|archive))",
        re.IGNORECASE,
    ), "malware_lure"),

    (re.compile(
        r"(account (will be|has been) (suspended|terminated|disabled|locked)|"
        r"immediate(ly)? (suspend|terminat|disabl)|"
        r"your access (will|has) (expire|been revoked))",
        re.IGNORECASE,
    ), "account_suspension"),
]

# ---------------------------------------------------------------------------
# Positive signals — need >= 2 to label as Junk
# ---------------------------------------------------------------------------
POSITIVE_SIGNALS = [
    (re.compile(
        r"(unsubscribe|opt.out|to (stop|remove yourself) (receiving|from)|"
        r"you('re| are) receiving this (because|as a)|"
        r"you (subscribed|signed up|requested) (to|for)|"
        r"manage (your )?(subscription|preferences)|"
        r"list-unsubscribe)",
        re.IGNORECASE,
    ), "mailing_list_marker"),

    (re.compile(
        r"(newsletter|digest|bulletin|weekly (update|roundup|report)|"
        r"daily (update|briefing|alert)|monthly (update|report|newsletter)|"
        r"tip of the (day|week))",
        re.IGNORECASE,
    ), "newsletter_digest"),

    (re.compile(
        r"(special offer|limited.time|exclusive (deal|offer|discount|access)|"
        r"save (up to|\d+%)|free (shipping|trial|demo|consultation)|"
        r"discount|promotion|promo code|coupon|sale (ends|on)|"
        r"today only|act now|don't miss)",
        re.IGNORECASE,
    ), "promotional_offer"),

    (re.compile(
        r"(webinar|register (now|today|here)|join us (for|on)|"
        r"save your seat|reserve your (spot|seat)|"
        r"free (event|workshop|seminar|session)|"
        r"you('re| are) invited)",
        re.IGNORECASE,
    ), "event_invite"),

    (re.compile(
        r"(we supply|our (services|products|solutions)|"
        r"vendor|supplier|B2B|business opportunity|grow your business|"
        r"we (help|assist|support) companies|"
        r"partnership (opportunity|proposal)|"
        r"quick question about|reaching out (about|regarding)|"
        r"I wanted to (connect|reach out|introduce))",
        re.IGNORECASE,
    ), "vendor_b2b_outreach"),

    (re.compile(
        r"(loyalty (points|rewards|program)|you('ve| have) earned \d|"
        r"redeem (your|now)|reward(s)? (points|balance)|"
        r"miles? (earned|balance|reward)|"
        r"congratulations.*you('ve| have) (won|qualified|been selected))",
        re.IGNORECASE,
    ), "loyalty_reward"),

    (re.compile(
        r"(bulk mail|marketing email|commercial message|"
        r"dear (subscriber|member|customer|traveler|investor|reader)|"
        r"as a (subscriber|member|customer|registered user)|"
        r"personalized (message|offer) from)",
        re.IGNORECASE,
    ), "bulk_marketing_style"),

    (re.compile(
        r"(click (here|below|the link) (to |for )?(learn|see|get|view|access|download|register)|"
        r"visit (our )?(website|site|store|page)|"
        r"view (this|the) (email|message) (in|online|as))",
        re.IGNORECASE,
    ), "bulk_cta"),
]


def check(rec: dict) -> tuple[str | None, int, list[str]]:
    """
    Returns (label, score, matched_signals).
    label is "junk" or None (discard).
    """
    text = rec["subject"] + " " + rec["body_text"]

    # Disqualifiers first
    for pattern, name in DISQUALIFIERS:
        if pattern.search(text):
            return None, 0, [f"DISQUALIFIED:{name}"]

    # Count positive signals
    matched = [name for pattern, name in POSITIVE_SIGNALS if pattern.search(text)]
    score = len(matched)

    if score >= 2:
        return "junk", score, matched
    return None, score, matched


def main():
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    kept, discarded_dq, discarded_low, total = 0, 0, 0, 0

    with open(IN_FILE, encoding="utf-8") as inf, \
         open(OUT_FILE, "w", encoding="utf-8") as outf:

        for line in inf:
            total += 1
            rec = json.loads(line)
            label, score, signals = check(rec)

            if label is None:
                if signals and signals[0].startswith("DISQUALIFIED"):
                    discarded_dq += 1
                else:
                    discarded_low += 1
                continue

            rec["label"] = label
            rec["junk_score"] = score
            rec["matched_signals"] = signals
            outf.write(json.dumps(rec) + "\n")
            kept += 1

    print(f"Total candidates : {total:,}")
    print(f"Labeled junk     : {kept:,}")
    print(f"Discarded (disqualifier) : {discarded_dq:,}")
    print(f"Discarded (low score)    : {discarded_low:,}")
    print(f"Output: {OUT_FILE}")


if __name__ == "__main__":
    main()
