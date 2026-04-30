"""
Phase 2.3 — Filter Enron parsed emails for external non-business Junk candidates.

Reads  data/interim/enron_parsed/enron_parsed.jsonl
Writes data/interim/junk_candidates/enron_junk_candidates.jsonl

Keep an email only if ALL of:
  1. From domain is not @enron.com
  2. Not a known Enron partner domain
  3. No phishing signals (credential language, auth failures, suspicious URLs)
  4. Content matches at least one Junk signal (promo, solicitation, event, mailing list)

Usage:
    python src/filter_enron.py
"""

import json
import re
from pathlib import Path

IN_FILE  = Path("data/interim/enron_parsed/enron_parsed.jsonl")
OUT_FILE = Path("data/interim/junk_candidates/enron_junk_candidates.jsonl")

# --- Exclusion lists ---

ENRON_DOMAINS = {"enron.com", "enron.net"}

# Major energy companies, law firms, financial counterparties Enron dealt with
PARTNER_DOMAINS = {
    # Energy companies
    "txu.com", "duke-energy.com", "williams.com", "reliantenergy.com",
    "dynegy.com", "el-paso.com", "elpaso.com", "pge.com", "pgecorp.com",
    "nisource.com", "columbiaenergygroup.com", "caiso.com", "nyiso.com",
    "nymex.com", "isda.org", "scientech.com", "pira.com",
    # Law firms
    "bracepatt.com", "velaw.com", "kslaw.com", "brobeck.com", "akllp.com",
    "gmssr.com", "govadv.com",
    # Financial / trading counterparties
    "americas.bnpparibas.com", "carrfut.com", "intcx.com",
    # Internal-adjacent (Enron subsidiaries / commissioners)
    "ccomad3.uu.commissioner.com",
}

# Personal freemail — individual person-to-person emails, not bulk/vendor Junk
FREEMAIL_DOMAINS = {
    "aol.com", "hotmail.com", "yahoo.com", "gmail.com", "msn.com",
    "earthlink.net", "bellsouth.net", "houston.rr.com", "worldnet.att.net",
    "compuserve.com", "prodigy.net", "juno.com",
}

# University / academic domains — not vendor or bulk mail
ACADEMIC_TLD_RE = re.compile(r'\.(edu|ac\.uk|ac\.in)$', re.IGNORECASE)

# --- Signal patterns ---

# Phishing disqualifiers — any match → discard
PHISHING_RE = re.compile(
    r"(verify your (account|identity|email|password)|confirm your (account|password|login)|"
    r"enter your (password|credentials|login|username)|"
    r"account (has been|will be) (suspended|locked|disabled|terminated)|"
    r"click here to (verify|confirm|restore|reactivate|unlock)|"
    r"your (account|access) (has been|is) (compromised|suspended|blocked)|"
    r"wire transfer|gift card|invoice payment|urgent transfer|"
    r"dear (beneficiary|customer|user),?\s*(your account)|"
    r"login to (avoid|prevent|restore))",
    re.IGNORECASE,
)

# Strong Junk signals — vendor/B2B/promotional intent
# At least ONE of these required (these are specific enough on their own)
STRONG_JUNK_RE = re.compile(
    r"(unsubscribe|you('re| are) receiving this (because|as)|"
    r"you (requested|subscribed|signed up) (to|for)|"
    r"to (stop|opt.out|remove yourself) (receiving|from)|"
    r"we supply|our (services|products|solutions) (can|will|are)|"
    r"vendor|supplier|B2B|business opportunity|grow your business|"
    r"free (trial|demo|consultation)|"
    r"webinar|register (now|today)|join us (for|on)|save your seat|"
    r"loyalty (points|rewards)|you('ve| have) earned \d|redeem (your|now)|"
    r"special offer (for|on|inside)|limited.time offer|exclusive (deal|offer|discount)|"
    r"congratulations.*you('ve| have) (won|been selected|qualified))",
    re.IGNORECASE,
)

# Weaker signals — need TWO of these to qualify (catches bulk promo without strong markers)
WEAK_JUNK_SIGNALS = [
    re.compile(r"(click here|click below|click the link)", re.IGNORECASE),
    re.compile(r"(dear (friend|member|subscriber|valued customer|colleague))", re.IGNORECASE),
    re.compile(r"(promotion|promotional|discount|offer|deal)", re.IGNORECASE),
    re.compile(r"(newsletter|mailing list|digest|bulletin)", re.IGNORECASE),
    re.compile(r"(act now|don't miss|don't wait|today only|expires soon)", re.IGNORECASE),
]

# Suspicious URL patterns (lookalike / URL shorteners / IP-based)
SUSPICIOUS_URL_RE = re.compile(
    r"(https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|"  # IP-based URL
    r"https?://(bit\.ly|tinyurl|t\.co|goo\.gl|ow\.ly)/)",
    re.IGNORECASE,
)

# Suspicious URL patterns (lookalike / URL shorteners / IP-based)
SUSPICIOUS_URL_RE = re.compile(
    r"(https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|"  # IP-based URL
    r"https?://(bit\.ly|tinyurl|t\.co|goo\.gl|ow\.ly)/)",
    re.IGNORECASE,
)


def is_partner_or_enron(domain: str) -> bool:
    if not domain:
        return True  # no domain → discard
    if any(domain == d or domain.endswith("." + d) for d in ENRON_DOMAINS):
        return True
    if any(domain == d or domain.endswith("." + d) for d in PARTNER_DOMAINS):
        return True
    if any(domain == d or domain.endswith("." + d) for d in FREEMAIL_DOMAINS):
        return True
    if ACADEMIC_TLD_RE.search(domain):
        return True
    return False


def has_phishing_signal(rec: dict) -> bool:
    text = (rec["subject"] + " " + rec["body_text"])
    if PHISHING_RE.search(text):
        return True
    # Auth failures are a phishing signal (though all Enron emails are "none")
    if rec["spf_result"] == "fail" or rec["dkim_result"] == "fail":
        return True
    # Suspicious URLs
    for url in rec["urls"]:
        if SUSPICIOUS_URL_RE.search(url):
            return True
    return False


def has_junk_signal(rec: dict) -> bool:
    text = rec["subject"] + " " + rec["body_text"]
    if STRONG_JUNK_RE.search(text):
        return True
    # Fallback: require at least 2 weak signals
    weak_hits = sum(1 for pattern in WEAK_JUNK_SIGNALS if pattern.search(text))
    return weak_hits >= 2


def main():
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    kept, total = 0, 0

    with open(IN_FILE, encoding="utf-8") as inf, \
         open(OUT_FILE, "w", encoding="utf-8") as outf:

        for line in inf:
            total += 1
            rec = json.loads(line)

            domain = rec["from_address"].split("@")[-1].lower() \
                     if "@" in rec["from_address"] else ""

            if is_partner_or_enron(domain):
                continue
            if has_phishing_signal(rec):
                continue
            if not has_junk_signal(rec):
                continue

            outf.write(json.dumps(rec) + "\n")
            kept += 1

    print(f"Total scanned : {total:,}")
    print(f"Kept (Junk candidates): {kept:,}")
    print(f"Output: {OUT_FILE}")


if __name__ == "__main__":
    main()
