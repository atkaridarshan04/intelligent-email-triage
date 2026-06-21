"""
promote_model.py — Promote a versioned checkpoint to production.

Updates the checkpoints/production symlink (or copies manifest on Windows),
logs the promotion event, and prints restart instructions.

Usage:
  python scripts/promote_model.py --version lightgbm-v20260614
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
CHECKPOINTS = ROOT / "checkpoints"
PROD = CHECKPOINTS / "production"
PROMOTION_LOG = CHECKPOINTS / "promotion_log.jsonl"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True, help="Checkpoint version dir name, e.g. lightgbm-v20260614")
    args = parser.parse_args()

    candidate = CHECKPOINTS / args.version
    if not candidate.exists():
        print(f"ERROR: {candidate} does not exist")
        sys.exit(1)

    manifest_path = candidate / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: manifest.json not found in {candidate}")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text())
    recall = manifest.get("metrics", {}).get("phishing_recall", "unknown")
    accuracy = manifest.get("metrics", {}).get("accuracy", "unknown")

    # Atomic promotion: remove old symlink/dir reference, create new one
    # On Linux/Mac: symlink. On Windows: copy manifest reference (no symlinks in WSL paths typically)
    try:
        if PROD.is_symlink():
            PROD.unlink()
        elif PROD.exists() and not PROD.is_dir():
            PROD.unlink()

        # Try symlink first; fall back to a redirect manifest
        try:
            os.symlink(candidate, PROD)
        except (OSError, NotImplementedError):
            # Windows fallback: copy all artifacts listed in manifest
            PROD.mkdir(exist_ok=True)
            import shutil
            shutil.copy(manifest_path, PROD / "manifest.json")
            for artifact in manifest.get("artifacts", {}).values():
                src = candidate / artifact
                if src.exists():
                    shutil.copy(src, PROD / artifact)

    except Exception as e:
        print(f"ERROR during promotion: {e}")
        sys.exit(1)

    # Log promotion event
    event = {
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "version": args.version,
        "phishing_recall": recall,
        "accuracy": accuracy,
    }
    with open(PROMOTION_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")

    print(f"Promoted {args.version} to production")
    print(f"  phishing_recall: {recall}")
    print(f"  accuracy:        {accuracy}")
    print(f"\nRestart the API to load the new model:")
    print(f"  uvicorn src.serving.api:app --reload")


if __name__ == "__main__":
    main()
