"""
build_dataset.py — Master dataset construction pipeline.

Usage:
    python3 scripts/build_dataset.py

Order (from dataset-plan.md):
  1. Parse all raw corpora
  2. Cross-dataset deduplication
  3. Kaggle quality audit
  4. Extract structured features
  5. Stratified sampling + manifest
  6. Quality gate check
  7. Save train/val/test parquet + manifest
"""
import csv
import gc
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1]))
csv.field_size_limit(10_000_000)

from src.datasets.balancing import build_dataset
from src.datasets.deduplication import deduplicate
from src.datasets.kaggle_audit import run_audit
from src.datasets.quality_gates import check
from src.datasets.schema import EmailRecord
from src.features.feature_pipeline import run as extract_features
from src.parsing.email_parser import load_directory, parse_csv, parse_json, parse_trec
from src.utils.io import email_id

DATA = Path("data")
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
INTERIM = DATA / "interim"

# Max rows read per source — prevents OOM on large CSVs.
# Final targets are 6K–12K records per class; 10K per source gives ample headroom after dedup.
MAX_ROWS_PER_SOURCE = 10_000

# Kaggle CSVs — (filename, source, default_label)
# CEAS_08: label 1=spam, 0=ham  (opposite convention — treat all as spam, skip ham via empty label)
# All others: label 0=spam, 1=phishing
KAGGLE_CSVS = [
    ("CEAS_08.csv",        "ceas",             "ceas"),  # handled separately below
    ("SpamAssasin.csv",    "spamassassin_csv", None),
    ("Enron.csv",          "enron",            None),
    ("Nazario.csv",        "nazario",          None),
    ("Nigerian_Fraud.csv", "nigerian_fraud",   None),
    ("Ling.csv",           "ling",           None),
    ("phishing_email.csv", "phishing_email", None),   # text_combined col — handled below
]


def _load_phishing_email_csv(path: Path, max_rows: int = 0) -> list[EmailRecord]:
    """phishing_email.csv has 'text_combined' instead of subject/body.
    Phishing rows (label=1) are concentrated after row ~39K, so we scan the full file
    but cap spam and phishing independently to avoid OOM.
    Per-label cap is max_rows // 2 so total output stays within max_rows.
    """
    records = []
    per_label_cap = (max_rows // 2) if max_rows else 999_999
    spam_count = phishing_count = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label_raw = str(row.get("label", "")).strip()
            label = "phishing" if label_raw == "1" else "spam"
            if label == "spam" and spam_count >= per_label_cap:
                continue
            if label == "phishing" and phishing_count >= per_label_cap:
                continue
            text = row.get("text_combined", "")
            rec = EmailRecord(
                subject="",
                body_text=text,
                label=label,
                source="phishing_email",
                era_bucket="mid",
            )
            rec.id = email_id(rec.subject, rec.body_text)
            records.append(rec)
            if label == "spam":
                spam_count += 1
            else:
                phishing_count += 1
            if spam_count >= per_label_cap and phishing_count >= per_label_cap:
                break
    return records


def _load_ceas_csv(path: Path, max_rows: int = 0) -> list[EmailRecord]:
    """CEAS_08.csv uses label 1=spam, 0=ham (inverted vs other Kaggle CSVs).
    We keep spam only. max_rows caps output records (spam rows), not input rows.
    """
    records = []
    with open(path, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if max_rows and len(records) >= max_rows:
                break
            if str(row.get("label", "")).strip() != "1":
                continue  # skip ham
            rec = EmailRecord(
                subject=row.get("subject", ""),
                body_text=row.get("body", ""),
                sender_address=row.get("sender", ""),
                reply_to=row.get("reply-to", ""),
                label="spam",
                source="ceas",
                era_bucket="mid",
            )
            rec.id = email_id(rec.subject, rec.body_text)
            records.append(rec)
    return records


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    INTERIM.mkdir(parents=True, exist_ok=True)

    all_records: list[EmailRecord] = []

    # --- Step 1: Parse all corpora ---
    print("Step 1: Parsing corpora...")

    # SpamAssassin raw .eml
    sa_dir = RAW / "spamassassin"
    if sa_dir.exists():
        recs = list(load_directory(sa_dir, source="spamassassin", default_label="spam", max_rows=MAX_ROWS_PER_SOURCE))
        print(f"  spamassassin (.eml): {len(recs)}")
        all_records.extend(recs)

    # TREC 2007 raw .eml via index
    trec_root = RAW / "trec" / "trec" / "trec07p"
    if trec_root.exists():
        recs = list(parse_trec(trec_root, source="trec", max_rows=MAX_ROWS_PER_SOURCE))
        print(f"  trec (.eml): {len(recs)}")
        all_records.extend(recs)

    # Kaggle CSVs
    kaggle_dir = RAW / "kaggle"
    if kaggle_dir.exists():
        for filename, source, _ in KAGGLE_CSVS:
            path = kaggle_dir / filename
            if not path.exists():
                continue
            if filename == "phishing_email.csv":
                # phishing rows (label=1) start after ~39K rows — cap per-label
                recs = _load_phishing_email_csv(path, max_rows=MAX_ROWS_PER_SOURCE)
            elif filename == "CEAS_08.csv":
                recs = _load_ceas_csv(path, max_rows=MAX_ROWS_PER_SOURCE)
            else:
                recs = list(parse_csv(path, source=source, max_rows=MAX_ROWS_PER_SOURCE))
            print(f"  {filename}: {len(recs)}")
            all_records.extend(recs)

    # Synthetic samples (Track B) — loaded after organic so dedup keeps organic on collision
    for label in ("phishing", "spam"):
        syn_dir = RAW / "synthetic" / label
        if syn_dir.exists():
            for jf in sorted(syn_dir.glob("*.json")):
                recs = list(parse_json(jf, source="synthetic"))
                print(f"  synthetic/{label}/{jf.name}: {len(recs)}")
                all_records.extend(recs)

    print(f"\nTotal parsed: {len(all_records)}")

    # --- Step 2: Kaggle quality audit ---
    print("\nStep 2: Kaggle quality audit...")
    audit = run_audit(RAW / "kaggle")
    (INTERIM / "kaggle_audit_result.json").write_text(json.dumps(audit, indent=2))
    print(f"  Kappa={audit['kappa']:.3f} → {audit['verdict'].upper()}")
    # We already loaded Kaggle above; if it fails, remove those records
    if not audit["passed"]:
        print("  Kaggle audit failed — removing Kaggle records.")
        kaggle_sources = {s for _, s, _ in KAGGLE_CSVS} | {"phishing_email"}
        all_records = [r for r in all_records if r.source not in kaggle_sources]

    # --- Step 3: Deduplication ---
    print("\nStep 3: Deduplication...")
    all_records = deduplicate(all_records)
    gc.collect()  # free pre-dedup list and MinHash LSH from memory
    print(f"  After dedup: {len(all_records)}")

    # Write shared domain/URL files
    from src.utils.io import extract_domain
    domains, urls = set(), set()
    for r in all_records:
        if r.sender_address:
            domains.add(extract_domain(r.sender_address))
        for u in r.urls:
            urls.add(u)
            domains.add(extract_domain(u))
    (INTERIM / "shared").mkdir(exist_ok=True)
    (INTERIM / "shared" / "domains.txt").write_text("\n".join(sorted(domains)))
    (INTERIM / "shared" / "urls.txt").write_text("\n".join(sorted(urls)))
    print(f"  Wrote {len(domains)} domains, {len(urls)} URLs to interim/shared/")

    # --- Step 4: Feature extraction ---
    print("\nStep 4: Extracting structured features...")
    for i, rec in enumerate(all_records):
        extract_features(rec)
        if i % 10000 == 0 and i > 0:
            print(f"  {i}/{len(all_records)}...")
    print("  Done.")

    # --- Step 5: Stratified sampling + split ---
    print("\nStep 5: Stratified sampling and splitting...")
    spam_count = sum(1 for r in all_records if r.label == "spam")
    phish_count = sum(1 for r in all_records if r.label == "phishing")
    print(f"  Available — spam: {spam_count}, phishing: {phish_count}")
    result = build_dataset(all_records)
    print(f"  Train: {len(result.train)} | Val: {len(result.val)} | Test: {len(result.test)}")

    # --- Step 6: Quality gates ---
    print("\nStep 6: Quality gate check...")
    gate_result = check(result.train + result.val + result.test)
    print(gate_result.report())
    if not gate_result.passed:
        print("\nDataset does not meet quality gates. Review above before training.")
        sys.exit(1)

    # --- Step 7: Save ---
    print("\nStep 7: Saving processed dataset...")

    def _to_df(records):
        rows = [{
            "id": r.id, "subject": r.subject, "body_text": r.body_text,
            "display_from_mismatch": r.display_from_mismatch,
            "reply_to_mismatch": r.reply_to_mismatch,
            "free_email_sender": r.free_email_sender,
            "url_count": r.url_count, "domain_count": r.domain_count,
            "shortened_url_present": r.shortened_url_present,
            "suspicious_tld_present": r.suspicious_tld_present,
            "ip_literal_url": r.ip_literal_url,
            "url_entropy": r.url_entropy,
            "typosquatting_detected": r.typosquatting_detected,
            "has_attachment": r.has_attachment,
            "attachment_type": r.attachment_type,
            "executable_detected": r.executable_detected,
            "macro_detected": r.macro_detected,
            "subject_length": r.subject_length, "body_length": r.body_length,
            "uppercase_ratio": r.uppercase_ratio, "digit_ratio": r.digit_ratio,
            "punctuation_density": r.punctuation_density,
            "link_density": r.link_density,
            "brand_mention": r.brand_mention,
            "sender_brand_mismatch": r.sender_brand_mismatch,
            "label": r.label, "source": r.source,
            "era_bucket": r.era_bucket, "subtype": r.subtype,
            "augmented": r.augmented, "split": r.split,
        } for r in records]
        return pd.DataFrame(rows)

    _to_df(result.train).to_parquet(PROCESSED / "train.parquet", index=False)
    _to_df(result.val).to_parquet(PROCESSED / "valid.parquet", index=False)
    _to_df(result.test).to_parquet(PROCESSED / "test.parquet", index=False)
    result.manifest.to_parquet(PROCESSED / "sampling_manifest.parquet", index=False)

    print(f"  Saved to {PROCESSED}/")
    print("\n✅ Dataset construction complete.")


if __name__ == "__main__":
    main()
