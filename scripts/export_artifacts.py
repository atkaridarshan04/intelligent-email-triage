"""
export_artifacts.py — Copy trained notebook artifacts into a checkpoint directory.

Usage:

  LightGBM (production):
    python scripts/export_artifacts.py --model lightgbm --source /path/to/kaggle/working

  Transformer (phase 3):
    python scripts/export_artifacts.py --model transformer --source /path/to/kaggle/working

  Both default to checkpoints/production/. Use --dest to target a versioned dir:
    python scripts/export_artifacts.py --model transformer --source /path/to/kaggle/working \\
        --dest checkpoints/transformer-v1.0

LightGBM expects in <source>:
    lgbm_phase2.txt, tfidf_phase2.pkl, calibrated_phase2.pkl

Transformer expects in <source>:
    roberta_hybrid_phase3.pt, phase3_temperature.pkl
"""
import argparse
import json
import pickle
import shutil
from pathlib import Path

ROOT = Path(__file__).parents[1]
DEFAULT_OUT = ROOT / "checkpoints" / "production"


def export_lightgbm(src: Path, out: Path):
    shutil.copy(src / "lgbm_phase2.txt", out / "lgbm.txt")
    print("Copied lgbm.txt")

    shutil.copy(src / "tfidf_phase2.pkl", out / "tfidf.pkl")
    print("Copied tfidf.pkl")

    with open(src / "calibrated_phase2.pkl", "rb") as f:
        calibrated = pickle.load(f)

    if hasattr(calibrated, "platt_a"):
        a, b = calibrated.platt_a, calibrated.platt_b
    else:
        print("WARNING: Could not extract Platt params — defaulting to identity (a=1.0, b=0.0).")
        print("Set real values manually in calibration.json after export.")
        a, b = 1.0, 0.0

    (out / "calibration.json").write_text(json.dumps({"a": a, "b": b}, indent=2))
    print(f"Wrote calibration.json (a={a:.4f}, b={b:.4f})")


def export_transformer(src: Path, out: Path):
    shutil.copy(src / "roberta_hybrid_phase3.pt", out / "roberta_hybrid_phase3.pt")
    print("Copied roberta_hybrid_phase3.pt")

    shutil.copy(src / "phase3_temperature.pkl", out / "phase3_temperature.pkl")
    with open(src / "phase3_temperature.pkl", "rb") as f:
        T = pickle.load(f)["T"]
    print(f"Copied phase3_temperature.pkl (T={T:.4f})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",  choices=["lightgbm", "transformer"], default="lightgbm")
    parser.add_argument("--source", required=True, help="Directory containing Kaggle output artifacts")
    parser.add_argument("--dest",   default=None,  help="Destination checkpoint dir (default: checkpoints/production/)")
    args = parser.parse_args()

    src = Path(args.source)
    out = Path(args.dest) if args.dest else DEFAULT_OUT
    out.mkdir(parents=True, exist_ok=True)

    if args.model == "lightgbm":
        export_lightgbm(src, out)
    else:
        export_transformer(src, out)

    print(f"\nArtifacts ready at {out}")


if __name__ == "__main__":
    main()
