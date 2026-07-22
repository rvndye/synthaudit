"""Module 5 — Leakage audit.

Target-centric screens: derived labels, label components, single-feature
dominance, duplicated targets, row-order/schedule leakage, and (optionally)
train/test contamination.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from ._util import SINGLE_FEATURE_FLAG, sample_df

SCREEN_SAMPLE = 30000


def _single_feature_score(x: pd.Series, y: pd.Series, task: str, seed=42) -> float:
    """Baseline-relative single-feature score in [0, 1].

    Missing values in a categorical feature are a category of their own
    (dropping them can silently reduce the target to one class and make any
    fit vacuous), and classification scores are reported as skill over the
    majority baseline, so extreme class imbalance cannot masquerade as
    predictive power.
    """
    if not pd.api.types.is_numeric_dtype(x):
        x = x.astype(object).where(x.notna(), "__missing__")
        ok = y.notna()
    else:
        ok = x.notna() & y.notna()
    if ok.sum() < 50:
        return 0.0
    xv = x[ok]
    if not pd.api.types.is_numeric_dtype(xv):
        xv = xv.astype("category").cat.codes
    X = xv.to_numpy(dtype=float).reshape(-1, 1)
    if task == "classification":
        yv = y[ok].astype(str).to_numpy()
        counts = pd.Series(yv).value_counts()
        if len(counts) < 2 or counts.iloc[1] < 20:
            return 0.0  # degenerate target slice: no evidence either way
        if len(counts) == 2:
            try:  # rank-based AUC for binary targets (imbalance-safe)
                yb = (yv == counts.index[1]).astype(int)
                auc = roc_auc_score(yb, X.ravel())
                return float(max(auc, 1 - auc))
            except Exception:
                pass
        t = DecisionTreeClassifier(max_depth=3, random_state=seed).fit(X, yv)
        acc = float(t.score(X, yv))
        base = float(counts.iloc[0] / counts.sum())
        return float(max(0.0, (acc - base) / (1 - base))) if base < 1 else 0.0
    yv = y[ok].to_numpy(dtype=float)
    if np.var(yv) == 0:
        return 0.0
    t = DecisionTreeRegressor(max_depth=4, random_state=seed).fit(X, yv)
    return float(max(t.score(X, yv), 0.0))


def run(
    df: pd.DataFrame,
    prof: dict,
    ident: dict,
    target: str | None,
    seed=42,
    test_df: pd.DataFrame | None = None,
) -> dict:
    findings = []

    # --- structure-level leakage (target-independent) ---
    if prof["duplicate_row_frac"] > 0.01:
        findings.append(
            {
                "kind": "duplicate_rows",
                "severity": "high",
                "detail": f"{prof['duplicate_rows']} exact duplicate rows "
                f"({100 * prof['duplicate_row_frac']:.2f}%) — random splits leak "
                f"identical records across folds (KDD'99 failure mode).",
            }
        )
    for f in ident["identities"]:
        if f["type"] == "duplicate_column" and f.get("exact"):
            findings.append(
                {
                    "kind": "duplicate_column",
                    "severity": "medium",
                    "detail": f"{f['target']} duplicates {f['predictors'][0]}.",
                }
            )
    for c in prof["constant_cols"]:
        findings.append(
            {
                "kind": "constant_column",
                "severity": "low",
                "detail": f"{c} is constant — carries no information.",
            }
        )

    out = {"findings": findings, "target": target}
    if target is None or target not in df.columns:
        out["note"] = "No target specified; target-level screens skipped."
        return out

    y = df[target]
    task = (
        "classification"
        if (not pd.api.types.is_numeric_dtype(y) or y.nunique(dropna=True) <= 20)
        else "regression"
    )
    out["task"] = task
    sub = sample_df(df, SCREEN_SAMPLE, seed)

    # --- derived target? (from identity mining, incl. constraint membership:
    #     an exact constraint containing the target makes it algebraically
    #     recoverable from the other members regardless of orientation) ---
    derived_evidence = []
    for f in ident["identities"]:
        members = f.get("constraint_members", [f["target"], *f.get("predictors", [])])
        fit = max(f.get("r2", 0) or 0, abs(f.get("corr", 0) or 0))
        if (f["target"] == target or target in members) and fit >= 0.995:
            derived_evidence.append(f)
    for r in ident["rule_derived_labels"]:
        if r["target"] == target:
            derived_evidence.append(r)
    if derived_evidence:
        best = max(derived_evidence, key=lambda f: f.get("fidelity", f.get("r2", 0)))
        findings.append(
            {
                "kind": "derived_target",
                "severity": "critical",
                "detail": f"Target '{target}' is (near-)recoverable by "
                f"{best['type']}: {best.get('equation', '')} "
                f"(fit={best.get('fidelity', best.get('r2')):.6f}). "
                f"Benchmark scores measure equation recovery, not learning.",
                "evidence": {k: v for k, v in best.items() if k != "rules"},
            }
        )

    # --- features derived FROM the target (post-outcome descendants) ---
    for f in ident["identities"]:
        if target in f.get("predictors", []) and f.get("r2", 0) >= 0.995 and f["target"] != target:
            findings.append(
                {
                    "kind": "target_descendant_feature",
                    "severity": "critical",
                    "detail": f"Feature '{f['target']}' is (near-)computed from the "
                    f"target: {f.get('equation', '')} (R²={f.get('r2'):.5f}) "
                    f"— post-outcome leakage.",
                }
            )

    # --- label components: features that appear in the target's derivation ---
    components = set()
    for f in derived_evidence:
        members = f.get("constraint_members", [f["target"], *f.get("predictors", [])])
        components.update(m for m in members if m != target)
    if components:
        findings.append(
            {
                "kind": "label_components",
                "severity": "critical",
                "detail": f"Columns {sorted(components)} functionally participate in "
                f"the target's generating rule — using them as features is "
                f"target leakage by construction.",
            }
        )

    # --- single-feature dominance ---
    screens = []
    for c in df.columns:
        if c == target or c in prof["id_cols"] or c in prof["datetime_cols"]:
            continue
        s = _single_feature_score(sub[c], sub[target], task, seed)
        screens.append({"feature": c, "score": round(s, 6)})
    screens.sort(key=lambda r: -r["score"])
    out["single_feature_screens"] = screens[:30]
    flagged = [s for s in screens if s["score"] >= SINGLE_FEATURE_FLAG]
    for s in flagged[:10]:
        sev = "critical" if s["score"] >= 0.99 else "high"
        findings.append(
            {
                "kind": "single_feature_dominance",
                "severity": sev,
                "detail": f"Feature '{s['feature']}' alone achieves "
                f"{s['score']:.4f} ({'AUC/acc' if task == 'classification' else 'R²'}) "
                f"on '{target}' — shortcut or leak candidate.",
            }
        )

    # --- row-order / schedule leakage ---
    try:
        yv = (
            y.astype("category").cat.codes
            if task == "classification"
            else pd.to_numeric(y, errors="coerce")
        )
        yv = yv.dropna().to_numpy(dtype=float)
        if len(yv) > 200 and np.var(yv) > 0:
            ac1 = float(np.corrcoef(yv[:-1], yv[1:])[0, 1])
            if abs(ac1) > 0.5:
                findings.append(
                    {
                        "kind": "row_order_structure",
                        "severity": "high",
                        "detail": f"Target lag-1 autocorrelation = {ac1:.3f}: rows are "
                        f"blocked/scheduled, not i.i.d. Random K-fold CV will "
                        f"leak regime context; use grouped or temporal splits.",
                    }
                )
            out["target_autocorrelation"] = round(ac1, 4)
    except Exception:
        pass

    # --- train/test contamination (optional) ---
    if test_df is not None:
        common = [c for c in df.columns if c in test_df.columns]
        h1 = pd.util.hash_pandas_object(df[common].round(6), index=False)
        h2 = pd.util.hash_pandas_object(test_df[common].round(6), index=False)
        overlap = len(set(h1) & set(h2))
        out["train_test_overlap_rows"] = int(overlap)
        out["train_test_overlap_frac"] = round(overlap / max(len(test_df), 1), 6)
        if overlap > 0:
            findings.append(
                {
                    "kind": "train_test_contamination",
                    "severity": "critical",
                    "detail": f"{overlap} rows shared between train and test splits.",
                }
            )

    sev_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    findings.sort(key=lambda f: -sev_rank.get(f["severity"], 0))
    out["n_critical"] = sum(1 for f in findings if f["severity"] == "critical")
    out["n_high"] = sum(1 for f in findings if f["severity"] == "high")
    return out
