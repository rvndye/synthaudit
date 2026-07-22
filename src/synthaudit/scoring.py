"""Module 6 — Benchmark Trustworthiness Index (BTI).

Five measured pillars, each in [0, 1] with an explicit estimator, aggregated
by a weighted geometric mean. The geometric mean is deliberately
non-compensatory: a single fatal artifact (pillar → 0) collapses the index,
because no amount of realism elsewhere rescues a benchmark whose label is a
shipped equation. The full pillar vector MUST be reported alongside the
scalar (single similarity-style scores are known to certify broken datasets —
Ganev & De Cristofaro 2025).

Pillars
-------
L  Label integrity      1 − excess of the best trivial-mechanism score over s0
F  Feature integrity    1 − (fraction of columns that are artifacts)
H  Difficulty headroom  1 − saturation of an honest model on the cleaned view
R  Sampling realism     mean of duplicate / autocorrelation / lattice subscores
I  Information density  effective linear rank of the numeric block / p
(T Transparency         optional, metadata-supplied; excluded when absent)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split

from ._util import encode_features, sample_df

S0 = 0.90  # trivial-mechanism tolerance for L
B_SAT = 0.995  # honest-model saturation reference for H
DEFAULT_WEIGHTS = {"L": 0.30, "F": 0.20, "H": 0.20, "R": 0.15, "I": 0.15}
GRADES = [(0.80, "A"), (0.65, "B"), (0.50, "C"), (0.35, "D"), (0.0, "F")]


def _excess(s: float, s0: float) -> float:
    return max(0.0, (s - s0) / (1 - s0)) if s0 < 1 else 0.0


def _honest_score(df, prof, taxonomy, target, seed=42) -> tuple[float, float, list]:
    """Out-of-sample score of a GBM on the cleaned (non-artifact) feature set."""
    bad_roles = {
        "target",
        "derived_deterministic",
        "label_component",
        "leaky_feature",
        "duplicate",
        "constant",
        "identifier",
        "datetime",
    }
    feats = [c for c, r in taxonomy["roles"].items() if r["role"] not in bad_roles and c != target]
    if target is None or target not in df.columns or not feats:
        return float("nan"), float("nan"), feats
    sub = sample_df(df[feats + [target]].dropna(subset=[target]), 20000, seed)
    X = encode_features(sub, feats, prof["categorical_cols"])
    if X.shape[1] == 0 or len(X) < 200:
        return float("nan"), float("nan"), feats
    y = sub[target]
    task_cls = (not pd.api.types.is_numeric_dtype(y)) or y.nunique() <= 20
    try:
        if task_cls:
            yv = y.astype(str).to_numpy()
            Xtr, Xte, ytr, yte = train_test_split(X, yv, test_size=0.33, random_state=seed)
            m = HistGradientBoostingClassifier(
                max_iter=150, random_state=seed, early_stopping=False
            )
            m.fit(Xtr, ytr)
            score = float(m.score(Xte, yte))
            base = float(pd.Series(yte).value_counts(normalize=True).iloc[0])
        else:
            yv = pd.to_numeric(y, errors="coerce").to_numpy(dtype=float)
            ok = np.isfinite(yv)
            Xtr, Xte, ytr, yte = train_test_split(X[ok], yv[ok], test_size=0.33, random_state=seed)
            m = HistGradientBoostingRegressor(max_iter=150, random_state=seed, early_stopping=False)
            m.fit(Xtr, ytr)
            score = float(max(m.score(Xte, yte), 0.0))
            base = 0.0
    except Exception:
        return float("nan"), float("nan"), feats
    return score, base, feats


def _effective_rank(df, prof, seed=42, exclude=()) -> float:
    cols = [
        c for c in prof["numeric_cols"] if c not in prof["constant_cols"] and c not in set(exclude)
    ]
    if len(cols) < 2:
        return 1.0
    sub = sample_df(df[cols].apply(pd.to_numeric, errors="coerce").dropna(), 15000, seed)
    if len(sub) < 100:
        return 1.0
    X = sub.to_numpy(dtype=float)
    Xs = (X - X.mean(0)) / np.where(X.std(0) > 0, X.std(0), 1.0)
    sv = np.linalg.svd(Xs, compute_uv=False)
    ev = sv**2 / (sv**2).sum()
    k999 = int(np.searchsorted(np.cumsum(ev), 0.999) + 1)
    return k999 / Xs.shape[1]


def run(df, prof, ident, det, leak, taxonomy, target, weights=None, metadata=None, seed=42) -> dict:
    w = dict(weights or DEFAULT_WEIGHTS)

    # --- L: label integrity ---
    trivial = 0.0
    evidence_L = []
    if target:
        for f in ident["identities"]:
            members = f.get("constraint_members", [f["target"], *f.get("predictors", [])])
            if f["target"] == target or target in members:
                fit = max(f.get("r2", 0.0) or 0.0, abs(f.get("corr", 0.0) or 0.0))
                trivial = max(trivial, fit)
                evidence_L.append(f.get("equation", f["type"]))
        for r in ident["rule_derived_labels"]:
            if r["target"] == target:
                trivial = max(trivial, r["fidelity"])
                evidence_L.append(r["equation"])
        for fd in ident.get("functional_dependencies", []):
            if fd["dependent"] == target:
                trivial = max(trivial, 1.0 - fd["g3_violation_rate"])
                evidence_L.append(fd["equation"])
        best_single = max(
            (s["score"] for s in leak.get("single_feature_screens", []) or []), default=0.0
        )
        trivial = max(trivial, best_single)
        for r in det.get("sweep", []):
            if r["column"] == target:
                trivial = max(trivial, r.get("skill", r["score"]))
    L = 1.0 - _excess(trivial, S0) if target else float("nan")

    # --- F: feature integrity ---
    counts = taxonomy["counts"]
    p = prof["n_cols"]
    bad = sum(
        counts.get(k, 0)
        for k in [
            "derived_deterministic",
            "label_component",
            "leaky_feature",
            "duplicate",
            "constant",
        ]
    )
    F = 1.0 - bad / max(p - 1, 1)

    # --- H: difficulty headroom ---
    honest, base, honest_feats = _honest_score(df, prof, taxonomy, target, seed)
    if np.isnan(honest):
        H = float("nan")
    else:
        rel = (honest - base) / (1 - base) if base < 1 else 0.0
        H = 1.0 - _excess(rel, B_SAT) if rel > 0 else 1.0

    # --- R: sampling realism ---
    r_dup = 1.0 - min(1.0, prof["duplicate_row_frac"] * 10)
    ac = abs(leak.get("target_autocorrelation", 0.0) or 0.0)
    r_ac = 1.0 - max(0.0, (ac - 0.5) / 0.5)
    n_num = max(len(prof["numeric_cols"]), 1)
    r_lat = 1.0 - len(prof.get("uniform_sampled_cols", [])) / n_num
    subs = [r_dup, r_ac, r_lat]
    if leak.get("train_test_overlap_frac") is not None:
        subs.append(1.0 - min(1.0, leak["train_test_overlap_frac"] * 10))
    R = float(np.mean(subs))

    # --- I: information density (on the stochastic core: derived columns
    #        are already charged to F; I measures core redundancy) ---
    I = float(_effective_rank(df, prof, seed, exclude=ident.get("derived_columns", [])))

    pillars = {"L": L, "F": F, "H": H, "R": R, "I": I}

    # --- T: transparency (optional, metadata-driven) ---
    if metadata:
        checks = [
            "generator_described",
            "generator_code_available",
            "seed_reported",
            "artifacts_disclosed",
        ]
        T = sum(bool(metadata.get(k)) for k in checks) / len(checks)
        pillars["T"] = T
        w.setdefault("T", 0.15)

    avail = {k: v for k, v in pillars.items() if not np.isnan(v)}
    wsum = sum(w[k] for k in avail)
    logbti = sum(w[k] / wsum * np.log(max(v, 0.01)) for k, v in avail.items())
    bti = float(np.exp(logbti))
    grade = next(g for t, g in GRADES if bti >= t)

    return {
        "pillars": {k: (None if np.isnan(v) else round(v, 4)) for k, v in pillars.items()},
        "weights": {k: w[k] for k in avail},
        "bti": round(bti, 4),
        "grade": grade,
        "evidence": {
            "trivial_mechanism_score": round(trivial, 6) if target else None,
            "label_evidence": evidence_L[:5],
            "artifact_columns": bad,
            "honest_model_score": None if np.isnan(honest) else round(honest, 4),
            "honest_baseline": None if np.isnan(honest) else round(base, 4),
            "honest_features_used": len(honest_feats),
        },
        "interpretation": (
            "BTI is a triage score: report the pillar vector, not just the "
            "scalar. Grade A/B: usable with the recommended feature view. "
            "C: quarantine flagged columns and re-benchmark. D/F: dataset "
            "measures generator recovery, not learning — unsuitable as an ML "
            "benchmark without redesign."
        ),
    }
