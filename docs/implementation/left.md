# What's Left

**Date:** 2026-06-21
**System status:** All build phases complete (A–F). 149 tests passing. Model plugin architecture in place.

One task remains before the system can run: add trained model artifacts.

---

## Add model artifacts ⚠️ Blocking

The inference pipeline, API, and demo UI are fully built. They load artifacts from `checkpoints/production/` at startup based on `manifest.json`. The artifacts themselves are not in the repo — they were produced on Kaggle.

### LightGBM (current production model)

Download from Kaggle Phase 2b notebook output: `lgbm_phase2.txt`, `tfidf_phase2.pkl`, `calibrated_phase2.pkl`

```bash
python scripts/export_artifacts.py --model lightgbm --source /path/to/kaggle/outputs
```

Writes `lgbm.txt`, `tfidf.pkl`, `calibration.json` into `checkpoints/production/`.

### Transformer (optional)

Download from Kaggle Phase 3 notebook output: `roberta_hybrid_phase3.pt`, `phase3_temperature.pkl`

```bash
python scripts/export_artifacts.py --model transformer \
    --source /path/to/kaggle/outputs \
    --dest checkpoints/transformer-v1.0
```

Then promote if desired:
```bash
python scripts/promote_model.py --version transformer-v1.0
```

---

## Verify

```bash
uvicorn src.serving.api:app --reload
curl http://localhost:8000/health
# {"status": "ok", "model_version": "lightgbm-v1.0"}
```

---

## Done — nothing else is blocking

See `QUICKSTART.md` for full setup and usage instructions.
