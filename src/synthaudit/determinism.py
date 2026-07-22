"""Module 3 — Determinism analysis.

Out-of-sample predictability sweep: how well can each column be predicted
from all the others? Near-perfect out-of-sample scores expose deterministic
or near-deterministic generator relationships that identity mining's
restricted function classes may miss.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.feature_selection import mutual_info_classif, mutual_info_regression
from sklearn.model_selection import train_test_split

from ._util import DET_SWEEP_HIGH, encode_features, sample_df

SWEEP_SAMPLE = 20000


def run(df: pd.DataFrame, prof: dict, seed=42, max_cols=60, exclude_predictors=None) -> dict:
    """exclude_predictors: derived/duplicate columns from identity mining —
    excluded from the predictor pool so the sweep measures predictability
    from the stochastic core, not from a column's own algebraic shadow."""
    excl = set(exclude_predictors or [])
    numeric = [c for c in prof["numeric_cols"] if c not in prof["constant_cols"]]
    cats = [c for c in prof["categorical_cols"] if c not in prof["constant_cols"]]
    targets = list(dict.fromkeys(numeric + cats))[:max_cols]
    feat_pool = [c for c in targets if c not in excl]

    sub = sample_df(df[list(dict.fromkeys(targets + feat_pool))], SWEEP_SAMPLE, seed)
    results = []
    for t in targets:
        feats = [c for c in feat_pool if c != t]
        if not feats:
            continue
        X = encode_features(sub, feats, cats)
        if X.shape[1] == 0:
            continue
        is_cat = (t in cats and not pd.api.types.is_numeric_dtype(df[t])) or (
            df[t].nunique(dropna=True) <= 20
        )
        try:
            if is_cat:
                y = sub[t].astype(str).to_numpy()
                if len(np.unique(y)) < 2:
                    continue
                Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.33, random_state=seed)
                m = HistGradientBoostingClassifier(
                    max_iter=120, random_state=seed, early_stopping=False
                )
                m.fit(Xtr, ytr)
                score = float(m.score(Xte, yte))
                base = float(pd.Series(yte).value_counts(normalize=True).iloc[0])
                mi = mutual_info_classif(X, y, random_state=seed, discrete_features=False)
                metric = "accuracy"
            else:
                y = pd.to_numeric(sub[t], errors="coerce").to_numpy(dtype=float)
                ok = np.isfinite(y)
                if ok.sum() < 100 or np.var(y[ok]) == 0:
                    continue
                Xtr, Xte, ytr, yte = train_test_split(
                    X[ok], y[ok], test_size=0.33, random_state=seed
                )
                m = HistGradientBoostingRegressor(
                    max_iter=120, random_state=seed, early_stopping=False
                )
                m.fit(Xtr, ytr)
                score = float(m.score(Xte, yte))
                base = 0.0
                mi = mutual_info_regression(X[ok], y[ok], random_state=seed)
                metric = "r2"
        except Exception:
            continue
        best_idx = int(np.argmax(mi)) if len(mi) else 0
        # classification scores are converted to skill over the majority
        # baseline before banding: raw accuracy on a 99.9%-constant column is
        # not evidence of determinism, only of imbalance
        if metric == "accuracy" and base < 1:
            eff = max(0.0, (score - base) / (1 - base))
        else:
            eff = score
        results.append(
            {
                "column": t,
                "metric": metric,
                "score": round(score, 6),
                "skill": round(eff, 6),
                "baseline": round(base, 4),
                "best_single_feature": X.columns[best_idx] if len(mi) else None,
                "best_single_mi": round(float(mi[best_idx]), 4) if len(mi) else 0.0,
                "class": (
                    "deterministic"
                    if eff >= 0.999
                    else "near_deterministic"
                    if eff >= DET_SWEEP_HIGH
                    else "highly_predictable"
                    if eff >= 0.9
                    else "stochastic"
                ),
            }
        )
    results.sort(key=lambda r: -r.get("skill", r["score"]))
    return {
        "sweep": results,
        "deterministic": [r["column"] for r in results if r["class"] == "deterministic"],
        "near_deterministic": [r["column"] for r in results if r["class"] == "near_deterministic"],
    }
