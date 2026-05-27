"""
quality_gates.py — Pre-training quality gate checks (from dataset-plan.md).

Gates:
  - Spam samples ≥ 5,000
  - Phishing samples ≥ 6,000
  - Phishing source diversity ≥ 3 distinct sources
    (proxy for campaign diversity; subtype-based gate applies after Track B augmentation)
  - Synthetic ratio ≤ 25%
  - Structural coverage: majority of samples have URL + sender + text stat features
"""
from dataclasses import dataclass

import pandas as pd

from data.schema import EmailRecord


@dataclass
class GateResult:
    passed: bool
    details: dict[str, dict]

    def report(self) -> str:
        lines = ["Quality Gate Report", "=" * 40]
        for gate, info in self.details.items():
            status = "✅ PASS" if info["passed"] else "❌ FAIL"
            lines.append(f"{status}  {gate}: {info['value']} (min: {info['required']})")
        lines.append("=" * 40)
        lines.append("OVERALL: PASSED" if self.passed else "OVERALL: FAILED — do not proceed to training")
        return "\n".join(lines)


def check(records: list[EmailRecord]) -> GateResult:
    train = [r for r in records if r.split == "train"]

    spam = [r for r in train if r.label == "spam"]
    phishing = [r for r in train if r.label == "phishing"]
    synthetic = [r for r in train if r.augmented]
    total = len(train)

    # Phishing source diversity: distinct sources in train phishing set.
    # Subtype-based campaign gate will apply after Track B synthetic augmentation.
    phishing_sources = len({r.source for r in phishing})
    synthetic_ratio = len(synthetic) / total if total else 1.0

    # Structural coverage: record has at least one URL feature OR sender feature OR text stat
    def _has_structural(r: EmailRecord) -> bool:
        return (
            r.url_count > 0 or r.shortened_url_present or r.suspicious_tld_present
            or r.display_from_mismatch or r.reply_to_mismatch or r.free_email_sender
            or r.body_length > 0
        )

    structural_coverage = sum(1 for r in train if _has_structural(r)) / total if total else 0.0

    gates = {
        "spam_samples": {
            "value": len(spam), "required": 5_000,
            "passed": len(spam) >= 5_000,
        },
        "phishing_samples": {
            "value": len(phishing), "required": 6_000,
            "passed": len(phishing) >= 6_000,
        },
        "phishing_source_diversity": {
            "value": phishing_sources, "required": 3,
            "passed": phishing_sources >= 3,
        },
        "synthetic_ratio": {
            "value": round(synthetic_ratio, 3), "required": "≤ 0.25",
            "passed": synthetic_ratio <= 0.25,
        },
        "structural_coverage": {
            "value": round(structural_coverage, 3), "required": "> 0.50",
            "passed": structural_coverage > 0.50,
        },
    }

    return GateResult(
        passed=all(g["passed"] for g in gates.values()),
        details=gates,
    )
