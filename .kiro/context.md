# Project Context — Intelligent Email Triage

## What This Project Is

A SOC tool that auto-classifies user-reported suspicious emails into 4 outcomes:
- **Spam** → auto-folder
- **Junk** → junk route
- **Phishing** → immediate alert
- **Analyst Review** → manual triage (triggered by confidence layer, NOT a trained class)

Model trains on 3 classes only: Spam | Junk | Phishing.
Architecture: RoBERTa (text) + MLP (metadata) + MLP (behavioral) → Fusion → 3-class softmax → Confidence Layer → routing.

---

## Current Status

**Phase:** Track B complete. Waiting for Track A parquet outputs for final merge.

Research and design phase complete. Track B dataset construction complete. Final merge (train/val/test split) pending Track A outputs.

---

## Docs Structure

```
docs/
  design/        → problem-statement, ai-solutions, classification-logic,
                   confidence-and-explainability, project-structure
  research/      → phishing-attacks, datasets
  implementation/
    dataset/     → dataset-plan, dataset-parallel-tracks, track-b-execution-plan, track-b-results
    training/    → (future) training runs, experiments
    inference/   → (future) inference pipeline docs
    deployment/  → (future) API, Docker, serving
  operations/    → feedback-loop, evaluation-approach
  assets/        → images
notes/           → local notes (not pushed to git)
  project-understanding.md
  track-b-concepts.md
```

---

## Dataset Construction — Two Parallel Tracks

### Track A (Teammate) — Spam & Phishing
- Datasets: TREC 2007, CEAS 2008, SpamAssassin spam, Nazario, IWSPA-AP, Kaggle
- Builds: spam class (~20k) + phishing class (~20k)
- Outputs: `shared/domains.txt`, `shared/ips.txt`, `shared/urls.txt` for Track B

### Track B (Me) — Junk Class + Feature Enrichment
- Datasets: Enron corpus, synthetic templates, external APIs
- Builds: Junk class (~15k) via weak supervision + synthetic generation
- Also runs: WHOIS, Spamhaus ZEN, PhishTank lookups (waits for Track A's shared files)

Full execution plan: `docs/implementation/track-b-execution-plan.md`

---

## Track B — Current Position

**Complete.** All phases done. Outputs ready for final merge with Track A.

### Track B Phases
| Phase | Status |
|---|---|
| 1 — Setup + TLD table | ✅ Done |
| 2.1 — Enron download | ✅ Done |
| 2.2 — Parse all emails | ✅ Done — 517,401 emails → `data/interim/enron_parsed/enron_parsed.jsonl` |
| 2.3 — Filter for Junk candidates | ✅ Done — 13,729 candidates → `data/interim/junk_candidates/enron_junk_candidates.jsonl` |
| 2.4 — Compute behavioral history | ✅ Done — `data/interim/enron_behavioral_history.json` |
| 3 — Synthetic Junk generation | ✅ Done — 10,000 samples → `data/interim/synthetic_junk/synthetic_junk.jsonl` |
| 4 — Apply Junk labeling rules | ✅ Done — 7,639 labeled → `data/interim/junk_candidates/junk_labeled.jsonl` |
| 5 — Behavioral simulation + noise injection | ✅ Done — `data/interim/synthetic_junk/synthetic_junk_noised.jsonl` |
| 6 — Gold set validation | ✅ Done — `data/interim/gold_set_500.jsonl` |
| 7 — External lookups | ✅ Done (partial — see limitations in track-b-results.md) |
| 8 — Merge + manifest | ✅ Done — `data/processed/junk_features.parquet` + `junk_manifest.csv` |

### Final Junk Pool
| Source | Count |
|---|---|
| Enron organic | 7,639 |
| Synthetic | 10,000 |
| **Total (parquet)** | **17,639** |

### Next Step
Wait for Track A: `data/processed/spam_features.parquet` + `data/processed/phishing_features.parquet`
Then run final merge → 70/15/15 stratified split → `train.parquet`, `valid.parquet`, `test.parquet`

---

## Key Design Decisions to Remember

- Analyst Review is NOT a trained class — triggered at inference by confidence layer
- Trust score = 0.6 × max_prob + 0.4 × margin_score (margin catches ambiguity)
- Security override: phishing_prob > 0.70 AND high-weight signal → escalate regardless of trust score
- Junk class built via weak supervision — no public dataset has it natively
- Gold set validation requires Kappa ≥ 0.75 — plan for 2 annotation rounds
- Augmented samples need metadata explicitly assigned (not inherited blindly)
- Behavioral simulation needs noise injection (~15% spam/junk get first_time_domain=True, ~10% phishing get sender_seen_before=True)
- Domain age unreliable for pre-2010 emails — flag domain_age_reliable=False in manifest
- Cross-dataset deduplication required before sampling (Nazario/IWSPA-AP/Kaggle overlap)
- BEC always routes to Analyst Review regardless of confidence — but still needs ~2k training samples

---

## Target Dataset Composition

| Class | Target |
|---|---|
| Spam | ~20,000 |
| Junk | ~15,000 |
| Phishing | ~20,000 |
| **Total** | **~55,000** |

Split: 70% train / 15% val / 15% test (stratified, temporally constrained where timestamps available)

---

## Success Criteria

| Metric | Target |
|---|---|
| Phishing recall | > 98% |
| Overall accuracy | > 95% |
| False positive rate | < 2% |
| AUC | > 0.97 |
| Analyst queue reduction | > 50% |
| Inference latency | < 300ms |

---

## How to Resume a Session

1. Read this file first
2. Check Track B phase table above for current position
3. Relevant docs: `docs/implementation/dataset/track-b-execution-plan.md` for step-by-step work
4. Concepts reference: `notes/track-b-concepts.md`
5. Implementation log: `notes/implementation-log.md` — decisions made, outputs, iterations
