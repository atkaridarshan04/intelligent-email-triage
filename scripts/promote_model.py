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


def promote_checkpoint(version: str) -> dict:
    candidate = CHECKPOINTS / version
    if not candidate.exists():
        return {"success": False, "error": f"{candidate} does not exist"}

    manifest_path = candidate / "manifest.json"
    if not manifest_path.exists():
        return {"success": False, "error": f"manifest.json not found in {candidate}"}

    manifest = json.loads(manifest_path.read_text())
    recall = manifest.get("metrics", {}).get("phishing_recall", "unknown")
    accuracy = manifest.get("metrics", {}).get("accuracy", "unknown")

    # Atomic promotion: remove old symlink/dir reference, create new one
    try:
        if PROD.is_symlink():
            PROD.unlink()
        elif PROD.exists() and not PROD.is_dir():
            PROD.unlink()

        # Try symlink first; fall back to copying artifacts (Windows/WSL)
        try:
            os.symlink(candidate, PROD)
        except (OSError, NotImplementedError):
            PROD.mkdir(exist_ok=True)
            import shutil
            shutil.copy(manifest_path, PROD / "manifest.json")
            for artifact in manifest.get("artifacts", {}).values():
                src = candidate / artifact
                if src.exists():
                    shutil.copy(src, PROD / artifact)

    except Exception as e:
        return {"success": False, "error": f"Promotion error: {e}"}

    # Log promotion event
    event = {
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "phishing_recall": recall,
        "accuracy": accuracy,
    }
    with open(PROMOTION_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")

    return {
        "success": True,
        "version": version,
        "phishing_recall": recall,
        "accuracy": accuracy,
        "manifest": manifest,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True, help="Checkpoint version dir name, e.g. lightgbm-v20260614")
    args = parser.parse_args()

    res = promote_checkpoint(args.version)
    if not res["success"]:
        print(f"ERROR: {res['error']}")
        sys.exit(1)

    print(f"Promoted {args.version} to production")
    print(f"  phishing_recall: {res['phishing_recall']}")
    print(f"  accuracy:        {res['accuracy']}")
    print(f"\nRestart the API or trigger hot-reload to load the new model:")
    print(f"  uvicorn src.serving.api:app --reload")


if __name__ == "__main__":
    main()
