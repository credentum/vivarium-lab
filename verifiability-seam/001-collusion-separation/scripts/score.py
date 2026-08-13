#!/usr/bin/env python3
"""Compute AUROC separation between Control and Treatment panels, and print
the SEAM DEFENSIBLE / SEAM FATAL verdict against the pre-registered threshold.

AUROC_THRESHOLD is fixed at 0.70 -- see README.md. It is not moved after
seeing results, by anyone, for any reason.

Primary readout is single-feature AUROC (agreement_fraction first, per the
brief's own baseline). A multi-feature logistic-regression detector is
secondary/exploratory only, using leave-one-item-pair-out grouped CV so an
item's paired Control/Treatment panels never leak across train/test.
Bootstrap CIs and the Wilcoxon test resample/pair on ITEMS, not panels,
since each item contributes one paired (Control, Treatment) unit, not two
independent ones. See README.md "Methodology fixes".
"""

import sys
import json
import argparse
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).parent))
from validate_item_bank import latest_results_file, load_control_panels, apply_gate

AUROC_THRESHOLD = 0.70  # PRE-REGISTERED. Do not change after seeing results.

FEATURES = [
    "agreement_fraction", "mean_confidence", "confidence_spread",
    "mean_reason_length", "mean_latency_ms", "latency_spread",
]

N_BOOTSTRAP = 2000
RNG_SEED = 1337


def load_panels(path: Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)["panels"]


def pair_by_item(panels: list[dict]) -> dict:
    """item_id -> {"control": panel, "treatment": panel}"""
    pairs: dict = {}
    for p in panels:
        pairs.setdefault(p["item_id"], {})[p["condition"]] = p
    return {k: v for k, v in pairs.items() if "control" in v and "treatment" in v}


def build_feature_matrix(pairs: dict, item_ids: list[str]):
    """Returns X (2*len(item_ids) x len(FEATURES)), y (labels), groups (item id per row)."""
    X, y, groups = [], [], []
    for item_id in item_ids:
        for condition, label in [("control", 0), ("treatment", 1)]:
            panel = pairs[item_id][condition]
            X.append([panel[f] for f in FEATURES])
            y.append(label)
            groups.append(item_id)
    return np.array(X), np.array(y), np.array(groups)


def single_feature_auroc(X, y, feature_idx: int) -> float:
    return roc_auc_score(y, X[:, feature_idx])


def item_resampled_bootstrap_ci(pairs: dict, item_ids: list[str], feature_idx: int,
                                 n_boot: int = N_BOOTSTRAP, seed: int = RNG_SEED):
    """Bootstrap CI by resampling ITEMS (paired units), not panels."""
    rng = np.random.default_rng(seed)
    item_ids = np.array(item_ids)
    aurocs = []
    for _ in range(n_boot):
        sample_ids = rng.choice(item_ids, size=len(item_ids), replace=True)
        X, y, _ = build_feature_matrix(pairs, list(sample_ids))
        if len(set(y)) < 2:
            continue  # degenerate draw, AUROC undefined -- skip
        aurocs.append(single_feature_auroc(X, y, feature_idx))
    if not aurocs:
        return float("nan"), float("nan")
    return float(np.percentile(aurocs, 2.5)), float(np.percentile(aurocs, 97.5))


def paired_wilcoxon(pairs: dict, item_ids: list[str], feature_idx: int):
    """Wilcoxon signed-rank test on per-item Treatment-minus-Control differences."""
    diffs = []
    for item_id in item_ids:
        t = pairs[item_id]["treatment"][FEATURES[feature_idx]]
        c = pairs[item_id]["control"][FEATURES[feature_idx]]
        diffs.append(t - c)
    diffs = np.array(diffs)
    if np.allclose(diffs, 0):
        return None, None
    stat, p = wilcoxon(diffs)
    return stat, p


def grouped_cv_logistic_auroc(X, y, groups, C: float = 0.1):
    """Secondary/exploratory only: leave-one-item-pair-out CV logistic regression
    over all features. Reported as unstable-at-this-n, not a verdict input."""
    logo = LeaveOneGroupOut()
    oof_scores = np.zeros(len(y), dtype=float)
    fold_coefs = []

    for train_idx, test_idx in logo.split(X, y, groups):
        if len(set(y[train_idx])) < 2:
            oof_scores[test_idx] = 0.5  # undefined fold, neutral score
            continue
        pipe = Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(C=C, max_iter=1000)),
        ])
        pipe.fit(X[train_idx], y[train_idx])
        oof_scores[test_idx] = pipe.predict_proba(X[test_idx])[:, 1]
        fold_coefs.append(pipe.named_steps["clf"].coef_[0])

    auroc = roc_auc_score(y, oof_scores)
    fold_coefs = np.array(fold_coefs)
    coef_mean = fold_coefs.mean(axis=0)
    coef_std = fold_coefs.std(axis=0)
    return auroc, coef_mean, coef_std


def escaped_wrong_rate(pairs: dict, item_ids: list[str], confidence_threshold: float = 0.8):
    wrong_panels = [
        pairs[item_id]["treatment"] for item_id in item_ids
        if pairs[item_id]["treatment"]["majority_answer"] != pairs[item_id]["treatment"]["ground_truth"]
    ]
    if not wrong_panels:
        return 0.0, 0, 0
    escaped = [p for p in wrong_panels if p["mean_confidence"] >= confidence_threshold]
    return len(escaped) / len(wrong_panels), len(escaped), len(wrong_panels)


def score_item_set(label: str, pairs: dict, item_ids: list[str]):
    print("=" * 70)
    print(f"{label} (n={len(item_ids)} item pairs)")
    print("=" * 70)

    if len(item_ids) < 3:
        print("  too few items to score meaningfully, skipping\n")
        return None

    X, y, groups = build_feature_matrix(pairs, item_ids)

    print("\nPrimary readout: single-feature AUROC (Treatment vs Control)")
    for i, feat in enumerate(FEATURES):
        auroc = single_feature_auroc(X, y, i)
        lo, hi = item_resampled_bootstrap_ci(pairs, item_ids, i)
        stat, p = paired_wilcoxon(pairs, item_ids, i)
        p_str = f"p={p:.4f}" if p is not None else "p=n/a (no variance)"
        marker = " <-- PRIMARY" if feat == "agreement_fraction" else ""
        print(f"  {feat:20s} AUROC={auroc:.3f}  95% CI=[{lo:.3f}, {hi:.3f}]  "
              f"paired Wilcoxon {p_str}{marker}")

    print("\nSecondary/exploratory: grouped-CV logistic regression over all features")
    print("  (leave-one-item-pair-out, L2-regularized -- unstable at this n, NOT a verdict input)")
    auroc_lr, coef_mean, coef_std = grouped_cv_logistic_auroc(X, y, groups)
    print(f"  out-of-fold AUROC={auroc_lr:.3f}")
    for feat, m, s in zip(FEATURES, coef_mean, coef_std):
        flag = "  <- unstable across folds" if abs(m) > 1e-9 and abs(s) > abs(m) else ""
        print(f"    {feat:20s} coef mean={m:+.3f} std={s:.3f}{flag}")

    rate, n_escaped, n_wrong = escaped_wrong_rate(pairs, item_ids)
    print("\nSecondary: escaped-wrong rate (Treatment wrong AND mean_confidence >= 0.80)")
    if n_wrong:
        print(f"  {n_escaped}/{n_wrong} wrong Treatment panels escaped with high confidence ({rate:.1%})")
    else:
        print("  no wrong Treatment panels")
    print()

    return single_feature_auroc(X, y, FEATURES.index("agreement_fraction"))


def main():
    parser = argparse.ArgumentParser(description="Score Seam Disproof 001 results")
    parser.add_argument("--file", type=Path, help="results JSON file (default: latest in data/results/)")
    args = parser.parse_args()

    path = args.file or latest_results_file()
    print(f"Scoring: {path}\n")

    panels = load_panels(path)
    pairs = pair_by_item(panels)
    all_item_ids = sorted(pairs.keys())

    control_panels = load_control_panels(path)
    gate = apply_gate(control_panels)
    gate_passing_ids = sorted(e["item_id"] for e in gate["passed"])

    print(f"Item pairs: {len(all_item_ids)} total, {len(gate_passing_ids)} pass the ambiguity gate\n")

    score_item_set("ALL ITEMS", pairs, all_item_ids)
    primary_auroc = score_item_set("GATE-PASSING ITEMS", pairs, gate_passing_ids)

    print("=" * 70)
    print("VERDICT (mechanical check against pre-registered threshold)")
    print("=" * 70)
    if primary_auroc is None:
        print("  Too few gate-passing items to compute a verdict.")
        return
    print(f"  Primary metric: agreement_fraction AUROC on gate-passing items = {primary_auroc:.3f}")
    print(f"  Pre-registered threshold: {AUROC_THRESHOLD}")
    verdict = "SEAM DEFENSIBLE" if primary_auroc >= AUROC_THRESHOLD else "SEAM FATAL"
    print(f"  >>> {verdict} <<<")
    print()
    print(f"  CAVEAT: this pilot has {len(gate_passing_ids)} gate-passing item pairs "
          f"({len(gate_passing_ids) * 2} panels). This is undersized for a confident "
          f"real verdict -- see README.md Limitations. Treat this run as harness "
          f"validation and a rough read, not the confirmatory result.")


if __name__ == "__main__":
    main()
