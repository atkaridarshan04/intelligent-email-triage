#!/usr/bin/env python3
import json
import hashlib
from pathlib import Path

import pandas as pd


DATA_FILES = {
    "train": "data/final_clean_v2/train.jsonl",
    "val": "data/final_clean_v2/val.jsonl",
    "test": "data/final_clean_v2/test.jsonl",
}

OUT = Path("deep_audit")
OUT.mkdir(exist_ok=True)


# ------------------------
# loading
# ------------------------

def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def normalize_text(text):
    if pd.isna(text):
        return ""
    return " ".join(str(text).lower().split())


def body_hash(text):
    return hashlib.sha256(normalize_text(text).encode()).hexdigest()


# ------------------------
# null analysis
# ------------------------

def null_report(df, split):
    report = []

    for col in df.columns:
        nulls = df[col].isna().sum()

        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object:
            empty = (df[col].fillna("").astype(str).str.strip() == "").sum()
        else:
            empty = None

        report.append({
            "column": col,
            "null_count": nulls,
            "null_pct": round(nulls / len(df) * 100, 3),
            "empty_string_count": empty,
        })

    pd.DataFrame(report).to_csv(OUT / f"{split}_nulls.csv", index=False)


# ------------------------
# numeric stats
# ------------------------

def numeric_report(df, split):
    numeric = df.select_dtypes(include=["number"])

    if numeric.empty:
        return

    stats = numeric.describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]).T
    stats.to_csv(OUT / f"{split}_numeric_stats.csv")


# ------------------------
# categorical
# ------------------------

def categorical_report(df, split):
    cat_cols = df.select_dtypes(include=["object", "string"]).columns

    summary = []

    for col in cat_cols:
        vc = df[col].value_counts(dropna=False)
        vc.to_csv(OUT / f"{split}_{col}_distribution.csv")

        summary.append({
            "column": col,
            "unique_values": df[col].nunique(dropna=False),
        })

    pd.DataFrame(summary).to_csv(OUT / f"{split}_categorical_summary.csv", index=False)


# ------------------------
# boolean
# ------------------------

def boolean_report(df, split):
    bool_cols = df.select_dtypes(include=["bool"]).columns

    rows = []

    for col in bool_cols:
        true_pct = df[col].mean() * 100
        rows.append({
            "column": col,
            "true_pct": round(true_pct, 3),
        })

    pd.DataFrame(rows).to_csv(OUT / f"{split}_boolean_summary.csv", index=False)


# ------------------------
# consistency checks
# ------------------------

def consistency_checks(df, split):
    issues = []

    if "has_attachment" in df.columns and "attachment_type" in df.columns:
        bad = df[(df["has_attachment"] == False) & (df["attachment_type"].notna())]
        issues.append(("attachment_inconsistency", len(bad)))

    if "body_length" in df.columns and "body_text" in df.columns:
        calc = df["body_text"].fillna("").astype(str).str.len()
        mismatch = (calc != df["body_length"]).sum()
        issues.append(("body_length_mismatch", mismatch))

    if "subject_length" in df.columns and "subject" in df.columns:
        calc = df["subject"].fillna("").astype(str).str.len()
        mismatch = (calc != df["subject_length"]).sum()
        issues.append(("subject_length_mismatch", mismatch))

    if "digit_ratio" in df.columns:
        bad = ((df["digit_ratio"] < 0) | (df["digit_ratio"] > 1)).sum()
        issues.append(("digit_ratio_out_of_bounds", bad))

    if "uppercase_ratio" in df.columns:
        bad = ((df["uppercase_ratio"] < 0) | (df["uppercase_ratio"] > 1)).sum()
        issues.append(("uppercase_ratio_out_of_bounds", bad))

    if "link_density" in df.columns:
        bad = ((df["link_density"] < 0) | (df["link_density"] > 1)).sum()
        issues.append(("link_density_out_of_bounds", bad))

    pd.DataFrame(issues, columns=["check", "count"]).to_csv(
        OUT / f"{split}_consistency_checks.csv",
        index=False
    )


# ------------------------
# overlap leakage
# ------------------------

def overlap_report(dfs):
    for split, df in dfs.items():
        df["__body_hash"] = df["body_text"].apply(body_hash)

    pairs = [("train", "val"), ("train", "test"), ("val", "test")]

    rows = []

    for a, b in pairs:
        overlap = set(dfs[a]["__body_hash"]) & set(dfs[b]["__body_hash"])
        rows.append({
            "pair": f"{a}-{b}",
            "overlap_count": len(overlap),
        })

    pd.DataFrame(rows).to_csv(OUT / "text_overlap.csv", index=False)


# ------------------------
# drift
# ------------------------

def drift_report(dfs):
    numeric_cols = dfs["train"].select_dtypes(include=["number"]).columns

    rows = []

    for col in numeric_cols:
        rows.append({
            "column": col,
            "train_mean": dfs["train"][col].mean(),
            "val_mean": dfs["val"][col].mean(),
            "test_mean": dfs["test"][col].mean(),
            "train_median": dfs["train"][col].median(),
            "val_median": dfs["val"][col].median(),
            "test_median": dfs["test"][col].median(),
        })

    pd.DataFrame(rows).to_csv(OUT / "numeric_drift.csv", index=False)


# ------------------------
# label leakage suspicion
# ------------------------

def label_signal(df, split):
    if "label" not in df.columns:
        return

    rows = []

    for col in df.columns:
        if col == "label":
            continue

        if pd.api.types.is_bool_dtype(df[col]):
            grouped = df.groupby("label")[col].mean().to_dict()
            rows.append({
                "feature": col,
                "signal": str(grouped)
            })

    pd.DataFrame(rows).to_csv(OUT / f"{split}_label_signal.csv", index=False)


# ------------------------
# main
# ------------------------

def main():
    dfs = {}

    for split, path in DATA_FILES.items():
        print(f"Loading {split}...")
        dfs[split] = load_jsonl(path)

    for split, df in dfs.items():
        print(f"Auditing {split}...")
        null_report(df, split)
        numeric_report(df, split)
        categorical_report(df, split)
        boolean_report(df, split)
        consistency_checks(df, split)
        label_signal(df, split)

    overlap_report(dfs)
    drift_report(dfs)

    print("Deep audit complete.")


if __name__ == "__main__":
    main()