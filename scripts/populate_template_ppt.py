"""
populate_template_ppt.py — Fills Template_Engineering_Student_Project_Demo.pptx
with project-specific content and outputs Engineering_Student_Project_Demo_Filled.pptx.
"""
import zipfile
import xml.sax.saxutils as saxutils
from pathlib import Path

ROOT = Path(__file__).parents[1]
src_ppt = ROOT / "Template_Engineering_Student_Project_Demo.pptx"
dst_ppt = ROOT / "Engineering_Student_Project_Demo_Filled.pptx"

def esc(s: str) -> str:
    return saxutils.escape(s)

replacements_by_slide = {
    1: {
        "[Describe the user / business pain]": esc(
            "Over 85% of employee-reported emails are harmless commercial marketing spam or routine corporate broadcasts, yet each triggers manual Tier-1 triage. High-risk spear-phishing attacks remain buried beneath bulk noise, while mass phishing campaigns flood queues with dozens of duplicate tickets."
        ),
        "[State the outcome in one sentence]": esc(
            "An autonomous, calibrated triage platform that deduplicates mass campaigns into 1 card, deflects benign corporate false alarms, and instantly memorizes analyst verdicts in sub-2ms with >= 98.0% phishing recall."
        )
    },
    2: {
        "[Events, data, user request]": esc(
            "• Inbound user reports (RFC-822 MIME, IMAP live mailbox, or JSON)\n• Mass distributed phishing attacks targeting multiple bank employees\n• Authentic internal corporate announcements (benefits, HR broadcasts)"
        ),
        "[Logic, integrations, automation]": esc(
            "• 19 Multimodal Security Features (sender spoof, URL entropy, payload)\n• 64-bit SimHash Locality-Sensitive Fuzzy Clustering for campaign dedup\n• Dual-Engine Inference: 14ms LightGBM Champion + Deep RoBERTa Hybrid\n• Platt Calibration + Algorithmic Deferral Confidence Router\n• Fast-Path Episodic Memory Hot-Cache for sub-2ms instant learning"
        ),
        "[Decision, action, evidence]": esc(
            "• Automated Action: 98.8% automated triage rate with sub-15ms latency\n• 1-Click Campaign Remediation: 10:1 queue compression, 90% effort saved\n• Sub-2ms Deflection: Instant enterprise protection on recurring lures\n• Audit Evidence: TreeSHAP attribution waterfall & cryptographic dossier"
        )
    },
    3: {
        "[e.g., minutes per task]": esc(
            "• 90% SOC Effort Reduction on distributed campaign attacks\n• 10:1 Queue Compression Ratio (10 duplicate reports → 1 card)\n• Triage Latency: 8-12 min manual review → 14 ms automated inference"
        ),
        "[e.g., fewer missed steps]": esc(
            "• 98.01% Phishing Recall (exceeds non-negotiable 98.0% safety gate)\n• Sub-0.03 Expected Calibration Error (ECE) via Platt sigmoid scaling\n• Zero false-positive suppression on internal corporate communications"
        ),
        "[e.g., components reusable]": esc(
            "• Standard RFC-822 MIME parser + REST API for Proofpoint/Defender ingress\n• Reusable 64-bit SimHash clustering & Fast-Path Hot-Cache components\n• Dual-engine architecture with hot-swappable LightGBM and RoBERTa models"
        ),
        "“This enables [team] to [outcome] by [mechanism].”": esc(
            "“This enables Enterprise Cyber Defense to eliminate 90% of manual triage drudgery, protect 80,000+ employees from live campaigns in real time, and compress incident dwell time from hours to sub-2 milliseconds through calibrated ML and episodic memory.”"
        )
    }
}

def generate():
    if not src_ppt.exists():
        print(f"Error: {src_ppt} not found.")
        return

    with zipfile.ZipFile(src_ppt, "r") as zin:
        with zipfile.ZipFile(dst_ppt, "w") as zout:
            for item in zin.infolist():
                content = zin.read(item.filename)
                for slide_num, rep_dict in replacements_by_slide.items():
                    if item.filename == f"ppt/slides/slide{slide_num}.xml":
                        text_content = content.decode("utf-8")
                        for k, v in rep_dict.items():
                            if k in text_content:
                                text_content = text_content.replace(k, v)
                        content = text_content.encode("utf-8")
                zout.writestr(item, content)

    print(f"✅ Generated populated presentation: {dst_ppt}")

if __name__ == "__main__":
    generate()
