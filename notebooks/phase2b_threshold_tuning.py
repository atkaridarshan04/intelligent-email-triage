# =============================================================================
# PHASE 2b — CALIBRATION FIX + THRESHOLD TUNING
# Add these cells at the bottom of the Phase 2 notebook (pashe2.ipynb)
# All variables (model, X_val, X_test, y_val, y_test, test_proba,
# raw_val_proba, platt_a, platt_b) are already in memory from Phase 2.
# =============================================================================


# ── CELL 11: Temperature scaling calibration ─────────────────────────────────
# Better than Platt scaling for tree models with extreme probability outputs.
# Fits a single scalar T on the validation set.
from scipy.special import expit, logit
from scipy.optimize import minimize_scalar
from sklearn.metrics import brier_score_loss
from sklearn.calibration import calibration_curve

raw_val_proba = model.predict(X_val)
raw_test_proba = model.predict(X_test)

def temperature_loss(T, raw, y):
    p = expit(logit(np.clip(raw, 1e-7, 1-1e-7)) / T)
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

result = minimize_scalar(temperature_loss, bounds=(0.1, 10.0), method="bounded",
                         args=(raw_val_proba, y_val))
T_opt = result.x

def temp_scale(raw, T):
    return expit(logit(np.clip(raw, 1e-7, 1-1e-7)) / T)

test_proba_temp = temp_scale(raw_test_proba, T_opt)
val_proba_temp  = temp_scale(raw_val_proba,  T_opt)

print(f"Optimal temperature T = {T_opt:.4f}")
print(f"Brier (Platt):       {brier_score_loss(y_test, test_proba):.4f}")
print(f"Brier (Temperature): {brier_score_loss(y_test, test_proba_temp):.4f}")


# ── CELL 12: ECE comparison — Platt vs Temperature ───────────────────────────
def compute_ece(y_true, proba, n_bins=10):
    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (proba >= bin_edges[i]) & (proba < bin_edges[i+1])
        if mask.sum() == 0:
            continue
        acc  = (y_true[mask] == (proba[mask] >= 0.5).astype(int)).mean()
        conf = proba[mask].mean()
        ece += mask.mean() * abs(acc - conf)
    return ece

ece_platt = compute_ece(y_test, test_proba)
ece_temp  = compute_ece(y_test, test_proba_temp)

print(f"ECE (Platt scaling):       {ece_platt:.4f}")
print(f"ECE (Temperature scaling): {ece_temp:.4f}")
print(f"Target:                    < 0.05")

# Calibration curves side by side
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, proba, title in [
    (axes[0], test_proba,      f"Platt Scaling (ECE={ece_platt:.3f})"),
    (axes[1], test_proba_temp, f"Temperature Scaling (ECE={ece_temp:.3f})"),
]:
    prob_true, prob_pred = calibration_curve(y_test, proba, n_bins=10)
    ax.plot(prob_pred, prob_true, "s-", label="Model")
    ax.plot([0, 1], [0, 1], "k--", label="Perfect")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")
    ax.set_title(title)
    ax.legend()
plt.tight_layout()
plt.show()

# Use whichever calibration is better going forward
best_proba = test_proba_temp if ece_temp < ece_platt else test_proba
best_label = "Temperature" if ece_temp < ece_platt else "Platt"
print(f"\nUsing {best_label} scaling for remaining analysis.")


# ── CELL 13: Threshold sweep ──────────────────────────────────────────────────
from sklearn.metrics import recall_score, precision_score, f1_score

thresholds = np.arange(0.05, 0.96, 0.05)
rows = []
for t in thresholds:
    pred = (best_proba >= t).astype(int)
    rows.append({
        "threshold":       round(t, 2),
        "phishing_recall": round(recall_score(y_test, pred, pos_label=1, zero_division=0), 4),
        "spam_precision":  round(precision_score(y_test, pred, pos_label=0, zero_division=0), 4),
        "f1_phishing":     round(f1_score(y_test, pred, pos_label=1, zero_division=0), 4),
    })

df_sweep = pd.DataFrame(rows)
print("=== THRESHOLD SWEEP — LightGBM (Test Set) ===")
print(df_sweep.to_string(index=False))


# ── CELL 14: Routing band analysis ───────────────────────────────────────────
def trust_score(p, w1=0.6, w2=0.4):
    return (w1 * np.maximum(p, 1-p) + w2 * np.abs(2*p - 1)) * 100

scores = trust_score(best_proba)
bands = [
    ("auto_classify",         scores > 90),
    ("auto_classify_monitor", (scores > 75) & (scores <= 90)),
    ("analyst_review",        (scores > 55) & (scores <= 75)),
    ("priority_review",       scores <= 55),
]

print(f"\n=== ROUTING BAND ANALYSIS — LightGBM ({best_label} calibration) ===")
print(f"{'Band':<28} {'Count':>6} {'%Total':>7} {'Ph.Recall':>10} {'FN Rate':>8}")
print("-" * 65)

total = len(y_test)
for band_name, mask in bands:
    if mask.sum() == 0:
        continue
    band_true = y_test[mask]
    band_pred = (best_proba[mask] >= 0.5).astype(int)
    ph_in_band = (band_true == 1).sum()
    fn_in_band = ((band_true == 1) & (band_pred == 0)).sum()
    ph_recall  = recall_score(band_true, band_pred, pos_label=1, zero_division=0) if ph_in_band > 0 else float("nan")
    fn_rate    = fn_in_band / ph_in_band if ph_in_band > 0 else 0.0
    print(f"{band_name:<28} {mask.sum():>6} {mask.sum()/total*100:>6.1f}%  {ph_recall:>9.4f}  {fn_rate:>7.4f}")


# ── CELL 15: PR curve ─────────────────────────────────────────────────────────
from sklearn.metrics import precision_recall_curve, average_precision_score

prec, rec, _ = precision_recall_curve(y_test, best_proba)
ap = average_precision_score(y_test, best_proba)

plt.figure(figsize=(7, 5))
plt.plot(rec, prec, label=f"LightGBM — {best_label} (AP={ap:.4f})")
plt.xlabel("Recall (Phishing)")
plt.ylabel("Precision (Phishing)")
plt.title("Precision-Recall Curve — LightGBM")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()


# ── CELL 16: Final summary ────────────────────────────────────────────────────
from sklearn.metrics import accuracy_score, roc_auc_score

pred_final = (best_proba >= 0.5).astype(int)
print("=== PHASE 2 FINAL SUMMARY (with best calibration) ===")
print(f"Calibration method:  {best_label} scaling")
print(f"ECE:                 {min(ece_platt, ece_temp):.4f}  (target < 0.05)")
print(f"Accuracy:            {accuracy_score(y_test, pred_final):.4f}")
print(f"Phishing Recall:     {recall_score(y_test, pred_final, pos_label=1):.4f}  (target > 0.98)")
print(f"Phishing Precision:  {precision_score(y_test, pred_final, pos_label=1):.4f}")
print(f"ROC-AUC:             {roc_auc_score(y_test, best_proba):.4f}")
print(f"Brier Score:         {brier_score_loss(y_test, best_proba):.4f}")
auto_mask = trust_score(best_proba) > 75
print(f"Auto-classify rate:  {auto_mask.mean()*100:.1f}%")
print(f"Ph. recall (auto):   {recall_score(y_test[auto_mask], pred_final[auto_mask], pos_label=1):.4f}")
