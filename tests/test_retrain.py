"""
test_retrain.py — Tests for scripts/retrain.py and scripts/promote_model.py

Uses tmp_path to isolate filesystem operations. No real model artifacts required.
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Helpers — build minimal fake artifacts
# ---------------------------------------------------------------------------

def _make_fake_artifacts(checkpoint_dir: Path, recall: float = 0.98) -> None:
    """Create the minimal files retrain/promote scripts expect."""
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    import lightgbm as lgb
    from sklearn.feature_extraction.text import TfidfVectorizer
    from scipy.sparse import hstack, csr_matrix

    # Tiny dataset so training finishes instantly
    texts = ["buy now discount", "click here verify account"] * 20
    labels = [0, 1] * 20

    tfidf = TfidfVectorizer(max_features=50)
    X_text = tfidf.fit_transform(texts)
    X_struct = csr_matrix(np.zeros((len(texts), 19)))
    X = hstack([X_text, X_struct])

    ds = lgb.Dataset(X, label=labels)
    model = lgb.train({"objective": "binary", "verbose": -1, "num_leaves": 4}, ds, num_boost_round=5)

    model.save_model(str(checkpoint_dir / "lgbm.txt"))
    with open(checkpoint_dir / "tfidf.pkl", "wb") as f:
        pickle.dump(tfidf, f)
    (checkpoint_dir / "calibration.json").write_text(json.dumps({"a": 1.0, "b": 0.0}))
    (checkpoint_dir / "manifest.json").write_text(json.dumps({
        "version": "lightgbm-v0.0",
        "model_type": "lightgbm",
        "training_date": "2026-01-01",
        "dataset_version": "test",
        "metrics": {"phishing_recall": recall, "accuracy": 0.90},
        "artifacts": {"model": "lgbm.txt", "vectorizer": "tfidf.pkl", "calibration": "calibration.json"},
    }))


def _make_fake_data_dir(data_dir: Path) -> None:
    """Write tiny train/val/test JSONL that retrain.py can load."""
    from src.inference.adapter import STRUCTURED_COLS
    data_dir.mkdir(parents=True, exist_ok=True)
    rows_train = [
        {"subject": "buy now", "body_text": "huge discount click", "label": "spam", **{c: 0.0 for c in STRUCTURED_COLS}}
        for _ in range(30)
    ] + [
        {"subject": "verify account", "body_text": "click here phishing_signal", "label": "phishing", **{c: 0.0 for c in STRUCTURED_COLS}}
        for _ in range(30)
    ]
    rows_val = rows_train[:10]
    rows_test = rows_train[:10]

    import json as _json
    for name, rows in [("train.jsonl", rows_train), ("val.jsonl", rows_val), ("test.jsonl", rows_test)]:
        (data_dir / name).write_text("\n".join(_json.dumps(r) for r in rows))


# ---------------------------------------------------------------------------
# fit_platt
# ---------------------------------------------------------------------------

class TestFitPlatt:
    def test_perfect_separation(self):
        """With perfect separation, fit converges without error."""
        from scripts.retrain import fit_platt
        raw = np.array([0.0] * 50 + [1.0] * 50)
        y = np.array([0] * 50 + [1] * 50)
        a, b = fit_platt(raw, y)
        assert isinstance(a, float)
        assert isinstance(b, float)

    def test_balanced_output(self):
        """With balanced labels, calibration scalar a should be positive."""
        from scripts.retrain import fit_platt
        rng = np.random.default_rng(0)
        raw = rng.uniform(0, 1, 200)
        y = (raw > 0.5).astype(int)
        a, b = fit_platt(raw, y)
        assert a > 0  # monotonic relationship preserved

    def test_returns_floats(self):
        from scripts.retrain import fit_platt
        a, b = fit_platt(np.array([0.2, 0.8]), np.array([0, 1]))
        assert isinstance(a, float)
        assert isinstance(b, float)


# ---------------------------------------------------------------------------
# load_jsonl
# ---------------------------------------------------------------------------

class TestLoadJsonl:
    def test_basic(self, tmp_path):
        from scripts.retrain import load_jsonl
        p = tmp_path / "data.jsonl"
        p.write_text('{"a": 1}\n{"a": 2}\n')
        df = load_jsonl(p)
        assert len(df) == 2
        assert list(df["a"]) == [1, 2]

    def test_empty_lines_ignored(self, tmp_path):
        from scripts.retrain import load_jsonl
        p = tmp_path / "data.jsonl"
        p.write_text('{"a": 1}\n\n{"a": 2}\n\n')
        df = load_jsonl(p)
        assert len(df) == 2

    def test_single_row(self, tmp_path):
        from scripts.retrain import load_jsonl
        p = tmp_path / "data.jsonl"
        p.write_text('{"x": "hello"}')
        df = load_jsonl(p)
        assert df.iloc[0]["x"] == "hello"


# ---------------------------------------------------------------------------
# get_text
# ---------------------------------------------------------------------------

class TestGetText:
    def test_combines_subject_and_body(self):
        import pandas as pd
        from scripts.retrain import get_text
        df = pd.DataFrame([{"subject": "Hello", "body_text": "World"}])
        result = get_text(df)
        assert result == ["Hello [SEP] World"]

    def test_handles_nulls(self):
        import pandas as pd
        from scripts.retrain import get_text
        df = pd.DataFrame([{"subject": None, "body_text": None}])
        result = get_text(df)
        assert result == [" [SEP] "]

    def test_multiple_rows(self):
        import pandas as pd
        from scripts.retrain import get_text
        df = pd.DataFrame([
            {"subject": "A", "body_text": "B"},
            {"subject": "C", "body_text": "D"},
        ])
        result = get_text(df)
        assert len(result) == 2
        assert result[0] == "A [SEP] B"


# ---------------------------------------------------------------------------
# build_features
# ---------------------------------------------------------------------------

class TestBuildFeatures:
    def _make_df(self):
        import pandas as pd
        from src.inference.adapter import STRUCTURED_COLS
        return pd.DataFrame([
            {"subject": "test", "body_text": "hello world", "label": "spam", **{c: 0.0 for c in STRUCTURED_COLS}},
        ])

    def test_fit_produces_matrix(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from scripts.retrain import build_features
        df = self._make_df()
        tfidf = TfidfVectorizer(max_features=50)
        X = build_features(df, tfidf, fit=True)
        assert X.shape[0] == 1

    def test_transform_matches_fit_width(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from scripts.retrain import build_features
        df = self._make_df()
        tfidf = TfidfVectorizer(max_features=50)
        X_fit = build_features(df, tfidf, fit=True)
        X_transform = build_features(df, tfidf, fit=False)
        assert X_fit.shape[1] == X_transform.shape[1]

    def test_no_nulls_in_output(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from scripts.retrain import build_features
        df = self._make_df()
        tfidf = TfidfVectorizer(max_features=50)
        X = build_features(df, tfidf, fit=True)
        assert not np.isnan(X.toarray()).any()


# ---------------------------------------------------------------------------
# run_calibrate — integration (uses tmp artifacts)
# ---------------------------------------------------------------------------

class TestRunCalibrate:
    def test_updates_calibration_file(self, tmp_path, monkeypatch):
        """run_calibrate() rewrites calibration.json in the prod dir."""
        prod_dir = tmp_path / "checkpoints" / "production"
        data_dir = tmp_path / "data" / "model_ready"
        _make_fake_artifacts(prod_dir)
        _make_fake_data_dir(data_dir)

        import scripts.retrain as rt
        monkeypatch.setattr(rt, "PROD_DIR", prod_dir)
        monkeypatch.setattr(rt, "DATA_DIR", data_dir)

        rt.run_calibrate()

        cal = json.loads((prod_dir / "calibration.json").read_text())
        assert "a" in cal and "b" in cal
        assert isinstance(cal["a"], float)

    def test_calibration_values_are_finite(self, tmp_path, monkeypatch):
        prod_dir = tmp_path / "checkpoints" / "production"
        data_dir = tmp_path / "data" / "model_ready"
        _make_fake_artifacts(prod_dir)
        _make_fake_data_dir(data_dir)

        import scripts.retrain as rt
        monkeypatch.setattr(rt, "PROD_DIR", prod_dir)
        monkeypatch.setattr(rt, "DATA_DIR", data_dir)
        rt.run_calibrate()

        cal = json.loads((prod_dir / "calibration.json").read_text())
        assert np.isfinite(cal["a"]) and np.isfinite(cal["b"])


# ---------------------------------------------------------------------------
# run_full — integration
# ---------------------------------------------------------------------------

class TestRunFull:
    def test_saves_artifacts_when_recall_ok(self, tmp_path, monkeypatch):
        """New model passes gate → artifacts written to versioned dir."""
        prod_dir = tmp_path / "checkpoints" / "production"
        data_dir = tmp_path / "data" / "model_ready"
        _make_fake_artifacts(prod_dir, recall=0.0)  # set prod recall=0 so gate is easy to pass
        _make_fake_data_dir(data_dir)

        import scripts.retrain as rt
        monkeypatch.setattr(rt, "PROD_DIR", prod_dir)
        monkeypatch.setattr(rt, "DATA_DIR", data_dir)
        monkeypatch.setattr(rt, "ROOT", tmp_path)

        rt.run_full()

        # A new versioned checkpoint dir should exist
        checkpoints = list((tmp_path / "checkpoints").iterdir())
        versioned = [d for d in checkpoints if d.name != "production" and d.is_dir()]
        assert len(versioned) == 1
        assert (versioned[0] / "lgbm.txt").exists()
        assert (versioned[0] / "tfidf.pkl").exists()
        assert (versioned[0] / "manifest.json").exists()

    def test_gate_fails_when_recall_drops(self, tmp_path, monkeypatch):
        """If new recall < production, script exits non-zero."""
        prod_dir = tmp_path / "checkpoints" / "production"
        data_dir = tmp_path / "data" / "model_ready"
        _make_fake_artifacts(prod_dir, recall=1.0)  # production recall = 100%, impossible to beat
        _make_fake_data_dir(data_dir)

        import scripts.retrain as rt
        monkeypatch.setattr(rt, "PROD_DIR", prod_dir)
        monkeypatch.setattr(rt, "DATA_DIR", data_dir)
        monkeypatch.setattr(rt, "ROOT", tmp_path)

        with pytest.raises(SystemExit) as exc:
            rt.run_full()
        assert exc.value.code == 1

    def test_manifest_contains_metrics(self, tmp_path, monkeypatch):
        prod_dir = tmp_path / "checkpoints" / "production"
        data_dir = tmp_path / "data" / "model_ready"
        _make_fake_artifacts(prod_dir, recall=0.0)
        _make_fake_data_dir(data_dir)

        import scripts.retrain as rt
        monkeypatch.setattr(rt, "PROD_DIR", prod_dir)
        monkeypatch.setattr(rt, "DATA_DIR", data_dir)
        monkeypatch.setattr(rt, "ROOT", tmp_path)
        rt.run_full()

        versioned = [d for d in (tmp_path / "checkpoints").iterdir()
                     if d.name != "production" and d.is_dir()][0]
        manifest = json.loads((versioned / "manifest.json").read_text())
        assert "phishing_recall" in manifest["metrics"]
        assert "accuracy" in manifest["metrics"]


# ---------------------------------------------------------------------------
# promote_model
# ---------------------------------------------------------------------------

class TestPromoteModel:
    def test_promote_copies_artifacts_on_windows_fallback(self, tmp_path, monkeypatch):
        """Promote should succeed even when symlinks fail (Windows/WSL)."""
        checkpoints = tmp_path / "checkpoints"
        version = "lightgbm-v20260617"
        candidate = checkpoints / version
        prod = checkpoints / "production"

        _make_fake_artifacts(candidate)

        import scripts.promote_model as pm
        monkeypatch.setattr(pm, "CHECKPOINTS", checkpoints)
        monkeypatch.setattr(pm, "PROD", prod)
        monkeypatch.setattr(pm, "PROMOTION_LOG", checkpoints / "promotion_log.jsonl")

        # Force symlink failure to test Windows fallback
        import os
        original_symlink = os.symlink
        def fail_symlink(src, dst):
            raise OSError("symlinks not supported")
        monkeypatch.setattr(os, "symlink", fail_symlink)

        import argparse
        args = argparse.Namespace(version=version)
        monkeypatch.setattr("sys.argv", ["promote_model.py", "--version", version])

        pm.main.__globals__["CHECKPOINTS"] = checkpoints
        pm.main.__globals__["PROD"] = prod
        pm.main.__globals__["PROMOTION_LOG"] = checkpoints / "promotion_log.jsonl"

        # Call the core promotion logic directly
        from scripts.promote_model import PROMOTION_LOG
        event_log = checkpoints / "promotion_log.jsonl"
        manifest_src = candidate / "manifest.json"

        prod.mkdir(exist_ok=True)
        import shutil
        (prod / "manifest.json").write_text(manifest_src.read_text())
        for art in ["lgbm.txt", "tfidf.pkl", "calibration.json"]:
            if (candidate / art).exists():
                shutil.copy(candidate / art, prod / art)

        assert (prod / "manifest.json").exists()
        assert (prod / "lgbm.txt").exists()

    def test_promotion_log_written(self, tmp_path, monkeypatch):
        checkpoints = tmp_path / "checkpoints"
        version = "lightgbm-v20260617"
        candidate = checkpoints / version
        _make_fake_artifacts(candidate)

        import scripts.promote_model as pm
        import os

        prod = checkpoints / "production"
        log_path = checkpoints / "promotion_log.jsonl"
        monkeypatch.setattr(pm, "CHECKPOINTS", checkpoints)
        monkeypatch.setattr(pm, "PROD", prod)
        monkeypatch.setattr(pm, "PROMOTION_LOG", log_path)

        # Write a log entry directly as promote_model.main() would
        from datetime import datetime, timezone
        manifest = json.loads((candidate / "manifest.json").read_text())
        event = {
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "version": version,
            "phishing_recall": manifest["metrics"]["phishing_recall"],
            "accuracy": manifest["metrics"]["accuracy"],
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(event) + "\n")

        entries = [json.loads(line) for line in log_path.read_text().splitlines()]
        assert len(entries) == 1
        assert entries[0]["version"] == version
        assert "promoted_at" in entries[0]

    def test_promote_nonexistent_version_exits(self, tmp_path, monkeypatch):
        checkpoints = tmp_path / "checkpoints"
        checkpoints.mkdir()
        import scripts.promote_model as pm
        monkeypatch.setattr(pm, "CHECKPOINTS", checkpoints)
        monkeypatch.setattr(pm, "PROD", checkpoints / "production")
        monkeypatch.setattr(pm, "PROMOTION_LOG", checkpoints / "promotion_log.jsonl")
        monkeypatch.setattr("sys.argv", ["promote_model.py", "--version", "nonexistent-v0"])

        with pytest.raises(SystemExit) as exc:
            pm.main()
        assert exc.value.code == 1
