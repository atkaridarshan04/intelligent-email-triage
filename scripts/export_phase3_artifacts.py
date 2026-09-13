"""
export_phase3_artifacts.py — Ingest and validate Phase 3 RoBERTa artifacts from Kaggle.

Usage:
  python scripts/export_phase3_artifacts.py --artifacts-dir /path/to/kaggle/download
"""
import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).parents[1]
PHASE3_DIR = ROOT / "checkpoints" / "phase3"


def main():
    parser = argparse.ArgumentParser(description="Stage Phase 3 RoBERTa artifacts")
    parser.add_argument("--artifacts-dir", required=True, help="Directory containing roberta_hybrid_phase3.pt and phase3_temperature.pkl")
    args = parser.parse_args()

    src_dir = Path(args.artifacts_dir)
    model_pt = src_dir / "roberta_hybrid_phase3.pt"
    temp_pkl = src_dir / "phase3_temperature.pkl"

    if not model_pt.exists():
        print(f"ERROR: {model_pt} does not exist.")
        return

    if not temp_pkl.exists():
        print(f"ERROR: {temp_pkl} does not exist.")
        return

    PHASE3_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(model_pt, PHASE3_DIR / "roberta_hybrid_phase3.pt")
    shutil.copy(temp_pkl, PHASE3_DIR / "phase3_temperature.pkl")

    manifest_file = PHASE3_DIR / "manifest.json"
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text())
        manifest["status"] = "ready"
        manifest_file.write_text(json.dumps(manifest, indent=2))

    print(f"Successfully staged Phase 3 artifacts in {PHASE3_DIR}!")
    print("Phase 3 RoBERTa model is now ready for testing and promotion.")


if __name__ == "__main__":
    main()
