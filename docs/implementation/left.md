# What's Left

**Date:** 2026-06-17
**System status:** All build phases complete (A–F). 149 tests passing.

One task remains before the system can run against real emails.

---

## 1. Export production model artifacts ⚠️ Blocking

The inference pipeline, API, and demo UI are fully built. They load artifacts from `checkpoints/production/` at startup. That directory has `manifest.json` and `calibration.json` but is missing the actual model files.

**Missing:**

| File | What it is |
|---|---|
| `checkpoints/production/lgbm.txt` | Trained LightGBM booster (Phase 2b) |
| `checkpoints/production/tfidf.pkl` | Fitted TF-IDF vectorizer (Phase 2b) |

**How to add them:**

Your Phase 2b notebook (`notebooks/pashe2b.ipynb`) produced these files on Kaggle. Download them and run:

```bash
python scripts/export_artifacts.py --source /path/to/kaggle/outputs
```

Expected source filenames: `lgbm_phase2.txt`, `tfidf_phase2.pkl`, `calibrated_phase2.pkl`.

If your notebook used different names, copy and rename manually:
```bash
cp /path/to/lgbm_phase2.txt   checkpoints/production/lgbm.txt
cp /path/to/tfidf_phase2.pkl  checkpoints/production/tfidf.pkl
```

Then verify the API starts cleanly:
```bash
uvicorn src.serving.api:app --reload
# → open http://localhost:8000/health
```

---

## 2. Verify calibration.json matches the exported model

`checkpoints/production/calibration.json` currently contains placeholder Platt scaling values (`a=1.0, b=0.0` — identity, no calibration applied). After exporting artifacts, confirm the values match what Phase 2b actually fitted. The export script extracts them automatically if the calibrated model pickle has `platt_a`/`platt_b` attributes.

If uncertain, run `--mode calibrate` after export to refit on the validation set:
```bash
python scripts/retrain.py --mode calibrate
```

---

## Done — nothing else is blocking

Once artifacts are in place:

| Task | How |
|---|---|
| Run the demo | `uvicorn src.serving.api:app --reload` → `http://localhost:8000/demo/` |
| Run in Docker | `docker-compose up` |
| Retrain on analyst feedback | `python scripts/retrain.py --mode full` |
| Promote a new model | `python scripts/promote_model.py --version lightgbm-vYYYYMMDD` |
