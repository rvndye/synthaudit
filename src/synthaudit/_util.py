"""Shared utilities for SynthAudit."""

from __future__ import annotations

import numpy as np
import pandas as pd

RNG_SEED = 42

# thresholds (documented in the paper; overridable via Audit config)
EXACT_R2 = 1 - 1e-9  # residual variance ratio for "exact" identities
NEAR_R2 = 0.995  # "near-deterministic" fit threshold
RULE_FIDELITY = 0.999  # shallow-tree fidelity for rule-derived labels
SINGLE_FEATURE_FLAG = 0.95  # single-feature performance flag
DET_SWEEP_HIGH = 0.98  # out-of-sample near-determinism
CONSTANT_TOL = 1e-12


def split_columns(df: pd.DataFrame, max_cat_card: int = 32):
    """Partition columns into numeric, categorical (low-card), and id-like."""
    numeric, categorical, idlike, datetime_cols = [], [], [], []
    n = len(df)
    for c in df.columns:
        s = df[c]
        if pd.api.types.is_datetime64_any_dtype(s):
            datetime_cols.append(c)
            continue
        if pd.api.types.is_numeric_dtype(s):
            nun = s.nunique(dropna=True)
            if nun <= 1:
                numeric.append(c)  # constants handled by profiler
            elif (
                nun <= min(max_cat_card, max(2, int(0.005 * n)))
                and (s.dropna() == s.dropna().round()).all()
                and nun <= max_cat_card
            ):
                # integer-coded low-cardinality -> treat as categorical AND numeric
                categorical.append(c)
                numeric.append(c)
            else:
                numeric.append(c)
        else:
            nun = s.nunique(dropna=True)
            if n > 0 and nun / max(n, 1) > 0.5 and nun > 1000:
                idlike.append(c)
            elif nun <= max_cat_card:
                categorical.append(c)
            else:
                idlike.append(c)
    return numeric, categorical, idlike, datetime_cols


def sample_df(df: pd.DataFrame, n: int, seed: int = RNG_SEED) -> pd.DataFrame:
    if len(df) <= n:
        return df
    return df.sample(n=n, random_state=seed)


def encode_features(df: pd.DataFrame, cols, cat_cols):
    """Ordinal-encode categoricals, passthrough numerics. Returns np array + names."""
    out = {}
    for c in cols:
        s = df[c]
        if c in cat_cols and not pd.api.types.is_numeric_dtype(s):
            out[c] = s.astype("category").cat.codes.to_numpy(dtype=float)
        elif pd.api.types.is_numeric_dtype(s):
            out[c] = pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)
    X = pd.DataFrame(out)
    X = X.replace([np.inf, -np.inf], np.nan)
    med = X.median(numeric_only=True)
    X = X.fillna(med).fillna(0.0)
    return X


def nice_round(x: float, tol: float = 1e-6):
    """Round coefficient to a 'nice' value if within tol (relative)."""
    if x == 0:
        return 0.0
    for nd in range(0, 7):
        r = round(x, nd)
        if r != 0 and abs(x - r) <= tol * max(1.0, abs(x)):
            return r
    return x


def fmt_equation(target: str, coefs: dict, intercept: float, kind: str = "linear") -> str:
    terms = []
    for k, v in coefs.items():
        if abs(v) < 1e-12:
            continue
        vv = nice_round(v, 1e-4)
        if kind == "loglinear":
            terms.append(f"{k}^{vv:g}")
        else:
            sign = "+" if vv >= 0 and terms else ""
            terms.append(f"{sign}{vv:g}*{k}" if terms else f"{vv:g}*{k}")
    if kind == "loglinear":
        c = np.exp(intercept)
        return f"{target} = {nice_round(c, 1e-4):g} * " + " * ".join(terms)
    ic = nice_round(intercept, 1e-4)
    eq = f"{target} = " + " ".join(terms)
    if abs(ic) > 1e-10:
        eq += f" {'+' if ic >= 0 else '-'} {abs(ic):g}"
    return eq
