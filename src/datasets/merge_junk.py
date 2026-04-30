"""
Phase 8 — Merge Junk samples into unified feature vectors + manifest.

Reads:
  data/interim/junk_candidates/junk_labeled.jsonl       (Enron, 7,639)
  data/interim/synthetic_junk/synthetic_junk_noised.jsonl (synthetic, 10,000)
  data/interim/enron_behavioral_history.json             (behavioral features for Enron)
  cache/phishtank/url_hits.json                          (URL reputation)
  cache/spamhaus/*.json                                  (IP reputation)

Writes:
  data/processed/junk_features.parquet   — unified feature vectors
  data/processed/junk_manifest.csv       — per-sample metadata for debugging/auditing

Feature vector schema (matches spec 8.2):
  Text:       subject, body_text, sender_display_name, url_token_text
  Metadata:   spf_result, dkim_result, dmarc_result, url_count, attachment_count,
              sender_domain_age_days, tld_risk_score, reply_to_mismatch,
              html_text_ratio, ip_listed, phishtank_hit
  Behavioral: sender_seen_before, communication_frequency, send_hour_deviation,
              first_time_domain

Note: sender_reputation_score, historical_sender_trust, campaign_burst_score,
lookalike_domain_detected are deferred to inference pipeline (require live computation).
domain_age_days=null for all records (WHOIS unavailable in this environment).

Usage:
    venv/bin/python src/datasets/merge_junk.py
"""

import json
import csv
import re
from datetime import datetime
from pathlib import Path
import pandas as pd
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.utils.tld_lookup import get_tld_score

# --- Paths ---
ENRON_FILE   = Path("data/interim/junk_candidates/junk_labeled.jsonl")
SYNTH_FILE   = Path("data/interim/synthetic_junk/synthetic_junk_noised.jsonl")
BH_FILE      = Path("data/interim/enron_behavioral_history.json")
PHISH_FILE   = Path("cache/phishtank/url_hits.json")
SPAMHAUS_DIR = Path("cache/spamhaus")
OUT_PARQUET  = Path("data/processed/junk_features.parquet")
OUT_MANIFEST = Path("data/processed/junk_manifest.csv")

IP_RE = re.compile(r'\b(\d{1,3}(?:\.\d{1,3}){3})\b')


def load_spamhaus() -> dict[str, bool | None]:
    """Returns {ip: listed|None}. None = error/unknown."""
    result = {}
    for f in SPAMHAUS_DIR.glob("*.json"):
        rec = json.loads(f.read_text())
        ip = rec.get("ip")
        if ip:
            result[ip] = None if rec.get("error") else rec.get("listed", False)
    return result


def extract_ips(headers: dict) -> list[str]:
    """Extract IPs from Received headers."""
    received = headers.get("Received", "") if isinstance(headers, dict) else ""
    return IP_RE.findall(received)


def parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    from email.utils import parsedate_to_datetime
    from datetime import timezone
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def era_bucket(date_str: str, augmented: bool) -> str:
    if augmented:
        return "recent"
    dt = parse_date(date_str)
    if dt is None:
        return "unknown"
    if dt.year < 2010:
        return "legacy"
    if dt.year < 2018:
        return "mid"
    return "recent"


def build_url_token_text(urls: list) -> str:
    """Tokenize URLs into space-separated domain tokens for text encoder."""
    tokens = []
    for url in urls:
        # strip scheme, replace punctuation with spaces
        token = re.sub(r'https?://', '', url)
        token = re.sub(r'[/\-_?=&.]', ' ', token)
        tokens.append(token.strip())
    return " ".join(tokens)


def process_enron(rec: dict, bh: dict, phish_hits: dict, spamhaus: dict) -> dict | None:
    file_key = rec["file"]
    behavioral = bh.get(file_key, {})

    domain = rec["from_address"].split("@")[-1].lower() if "@" in rec["from_address"] else ""
    ips = extract_ips(rec.get("headers", {}))
    ip_listed = None
    for ip in ips:
        val = spamhaus.get(ip)
        if val is True:
            ip_listed = True
            break
        if val is False:
            ip_listed = False

    url_list = rec.get("urls", [])
    phishtank_hit = any(phish_hits.get(u, False) for u in url_list)

    dt = parse_date(rec.get("date", ""))
    domain_age_reliable = False  # pre-2010 Enron emails + WHOIS unavailable

    return {
        # identifiers
        "file":                   file_key,
        "label":                  "junk",
        "augmented":              False,
        "source":                 "enron",
        "domain_age_reliable":    domain_age_reliable,
        # text
        "subject":                rec.get("subject", ""),
        "body_text":              rec.get("body_text", ""),
        "sender_display_name":    rec.get("sender_display_name", ""),
        "url_token_text":         build_url_token_text(url_list),
        # metadata
        "spf_result":             rec.get("spf_result", "none"),
        "dkim_result":            rec.get("dkim_result", "none"),
        "dmarc_result":           rec.get("dmarc_result", "none"),
        "url_count":              len(url_list),
        "attachment_count":       len(rec.get("attachments", [])),
        "sender_domain_age_days": None,   # WHOIS unavailable
        "tld_risk_score":         get_tld_score(domain),
        "reply_to_mismatch":      rec.get("reply_to_mismatch", False),
        "html_text_ratio":        rec.get("html_text_ratio", 0.0),
        "ip_listed":              ip_listed,
        "phishtank_hit":          phishtank_hit,
        # behavioral
        "sender_seen_before":     behavioral.get("sender_seen_before", False),
        "communication_frequency": behavioral.get("communication_frequency", 0),
        "send_hour_deviation":    behavioral.get("send_hour_deviation", 0.0),
        "first_time_domain":      behavioral.get("first_time_domain", True),
        # manifest fields
        "date":                   rec.get("date", ""),
        "era_bucket":             era_bucket(rec.get("date", ""), False),
        "subtype":                "organic_junk",
    }


def process_synthetic(rec: dict, phish_hits: dict) -> dict:
    url_list = rec.get("urls", [])
    phishtank_hit = any(phish_hits.get(u, False) for u in url_list)

    return {
        # identifiers
        "file":                   rec["file"],
        "label":                  "junk",
        "augmented":              True,
        "source":                 "synthetic",
        "domain_age_reliable":    rec.get("domain_age_reliable", True),
        # text
        "subject":                rec.get("subject", ""),
        "body_text":              rec.get("body_text", ""),
        "sender_display_name":    rec.get("sender_display_name", ""),
        "url_token_text":         build_url_token_text(url_list),
        # metadata
        "spf_result":             rec.get("spf_result", "pass"),
        "dkim_result":            rec.get("dkim_result", "none"),
        "dmarc_result":           rec.get("dmarc_result", "none"),
        "url_count":              rec.get("url_count", 0),
        "attachment_count":       rec.get("attachment_count", 0),
        "sender_domain_age_days": rec.get("sender_domain_age_days"),
        "tld_risk_score":         rec.get("tld_risk_score", 1),
        "reply_to_mismatch":      rec.get("reply_to_mismatch", False),
        "html_text_ratio":        rec.get("html_text_ratio", 0.0),
        "ip_listed":              None,   # synthetic — no real IP
        "phishtank_hit":          phishtank_hit,
        # behavioral
        "sender_seen_before":     rec.get("sender_seen_before", False),
        "communication_frequency": rec.get("communication_frequency", 0),
        "send_hour_deviation":    rec.get("send_hour_deviation", 0.0),
        "first_time_domain":      rec.get("first_time_domain", True),
        # manifest fields
        "date":                   "",
        "era_bucket":             "recent",
        "subtype":                rec.get("category", "synthetic_junk"),
    }


def main():
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)

    print("Loading lookup tables...")
    bh         = json.loads(BH_FILE.read_text())
    phish_hits = json.loads(PHISH_FILE.read_text())
    spamhaus   = load_spamhaus()
    print(f"  Behavioral history: {len(bh):,} entries")
    print(f"  PhishTank hits    : {sum(v for v in phish_hits.values() if v):,} / {len(phish_hits):,}")
    print(f"  Spamhaus cache    : {len(spamhaus):,} IPs")

    records = []
    dropped = 0

    # --- Enron ---
    print("\nProcessing Enron records...")
    with open(ENRON_FILE, encoding="utf-8") as f:
        for line in f:
            rec = process_enron(json.loads(line), bh, phish_hits, spamhaus)
            if rec is None:
                dropped += 1
                continue
            # Drop if missing > 2 metadata/behavioral features
            meta_behavioral = ["spf_result", "dkim_result", "dmarc_result",
                               "tld_risk_score", "sender_seen_before",
                               "communication_frequency", "send_hour_deviation",
                               "first_time_domain"]
            missing = sum(1 for k in meta_behavioral if rec.get(k) is None)
            if missing > 2:
                dropped += 1
                continue
            records.append(rec)
    print(f"  Enron: {sum(1 for r in records if r['source']=='enron'):,} kept")

    # --- Synthetic ---
    print("Processing synthetic records...")
    with open(SYNTH_FILE, encoding="utf-8") as f:
        for line in f:
            rec = process_synthetic(json.loads(line), phish_hits)
            records.append(rec)
    print(f"  Synthetic: {sum(1 for r in records if r['source']=='synthetic'):,} kept")

    print(f"\nTotal: {len(records):,}  Dropped: {dropped:,}")

    # --- Write parquet ---
    df = pd.DataFrame(records)
    # Separate manifest columns from feature columns
    manifest_cols = ["file", "source", "era_bucket", "subtype", "label",
                     "augmented", "domain_age_reliable", "date"]
    feature_cols  = [c for c in df.columns if c not in manifest_cols]

    df[feature_cols + ["file", "label"]].to_parquet(OUT_PARQUET, index=False)
    print(f"Parquet written: {OUT_PARQUET}")

    # --- Write manifest ---
    df[manifest_cols].to_csv(OUT_MANIFEST, index=False)
    print(f"Manifest written: {OUT_MANIFEST}")

    # --- Summary stats ---
    print(f"\nFeature coverage:")
    for col in ["sender_domain_age_days", "ip_listed", "phishtank_hit",
                "sender_seen_before", "tld_risk_score"]:
        null_count = df[col].isna().sum()
        print(f"  {col}: {len(df)-null_count:,} present, {null_count:,} null")

    print(f"\nEra distribution:")
    print(df["era_bucket"].value_counts().to_string())


if __name__ == "__main__":
    main()
