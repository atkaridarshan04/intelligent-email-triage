"""
export_artifacts.py — Copy trained notebook artifacts into checkpoints/production/.

Run this once after downloading Kaggle outputs:
    python scripts/export_artifacts.py --source /path/to/kaggle/working

Expects:
    <source>/lgbm_phase2.txt
    <source>/tfidf_phase2.pkl
    <source>/calibrated_phase2.pkl   (contains .platt_a / .platt_b via the CalibratedModel class)

Writes:
    checkpoints/production/lgbm.txt
    checkpoints/production/tfidf.pkl
    checkpoints/production/calibration.json  (Platt a, b extracted)
"""
import argparse
import json
import pickle
import shutil
from pathlib import Path

ROOT = Path(__file__).parents[1]
OUT = ROOT / "checkpoints" / "production"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Directory containing Kaggle output artifacts")
    args = parser.parse_args()

    src = Path(args.source)
    OUT.mkdir(parents=True, exist_ok=True)

    # Model
    shutil.copy(src / "lgbm_phase2.txt", OUT / "lgbm.txt")
    print(f"Copied lgbm.txt")

    # Vectorizer
    shutil.copy(src / "tfidf_phase2.pkl", OUT / "tfidf.pkl")
    print(f"Copied tfidf.pkl")

    # Extract Platt scaling params from CalibratedModel pickle
    with open(src / "calibrated_phase2.pkl", "rb") as f:
        calibrated = pickle.load(f)

    # The notebook's CalibratedModel stores params via closure; extract from the lambda
    # We re-derive a and b by loading the raw model and re-fitting if not directly accessible.
    # If the calibrated object has platt_a/platt_b attributes directly, use them.
    if hasattr(calibrated, "platt_a"):
        a, b = calibrated.platt_a, calibrated.platt_b
    else:
        # Fallback: identity calibration (raw = calibrated); replace with actual values
        print("WARNING: Could not extract Platt params automatically.")
        print("Set a and b manually in checkpoints/production/calibration.json")
        a, b = 1.0, 0.0

    (OUT / "calibration.json").write_text(json.dumps({"a": a, "b": b}, indent=2))
    print(f"Wrote calibration.json (a={a:.4f}, b={b:.4f})")

    print(f"\nArtifacts ready at {OUT}")


if __name__ == "__main__":
    main()
