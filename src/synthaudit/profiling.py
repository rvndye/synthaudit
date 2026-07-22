"""Module 1 — Dataset profiling.

Variable types, missingness, cardinality, constants, duplicates, outliers,
lattice/quantization artifacts, and marginal-shape diagnostics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from ._util import split_columns


def _lattice_check(s: pd.Series) -> dict:
    """Detect values lying on an exact arithmetic lattice (simulator grids)."""
    v = pd.to_numeric(s, errors="coerce").dropna().unique()
    if len(v) < 20:
        return {"on_lattice": False, "n_unique": int(len(v))}
    v = np.sort(v)
    d = np.diff(v)
    d = d[d > 0]
    if len(d) == 0:
        return {"on_lattice": False, "n_unique": int(len(v))}
    step = np.min(d)
    if step <= 0:
        return {"on_lattice": False, "n_unique": int(len(v))}
    ratio = d / step
    on = np.allclose(ratio, np.round(ratio), atol=1e-6)
    return {
        "on_lattice": bool(on and len(v) < 0.5 * len(s)),
        "step": float(step) if on else None,
        "n_unique": int(len(v)),
    }


def _uniformity_check(s: pd.Series) -> dict:
    """KS test against uniform on observed range — flags 'sampled inputs'."""
    v = pd.to_numeric(s, errors="coerce").dropna().to_numpy()
    if len(v) < 100 or v.min() == v.max():
        return {"uniform_like": False}
    u = (v - v.min()) / (v.max() - v.min())
    ks = stats.kstest(u, "uniform")
    return {"uniform_like": bool(ks.statistic < 0.02), "ks_stat": float(ks.statistic)}


def profile(df: pd.DataFrame, max_cat_card: int = 32) -> dict:
    n, p = df.shape
    numeric, categorical, idlike, dt = split_columns(df, max_cat_card)

    columns = {}
    constants, lattice_cols, uniform_cols = [], [], []
    for c in df.columns:
        s = df[c]
        nun = int(s.nunique(dropna=True))
        miss = float(s.isna().mean())
        entry = {
            "dtype": str(s.dtype),
            "n_unique": nun,
            "missing_frac": round(miss, 6),
            "role_hint": (
                "identifier"
                if c in idlike
                else "categorical"
                if c in categorical and c not in numeric
                else "numeric"
                if c in numeric
                else "other"
            ),
        }
        if nun <= 1:
            entry["constant"] = True
            constants.append(c)
        if pd.api.types.is_numeric_dtype(s) and nun > 1:
            v = pd.to_numeric(s, errors="coerce")
            entry.update(
                {
                    "mean": float(v.mean()),
                    "std": float(v.std()),
                    "min": float(v.min()),
                    "max": float(v.max()),
                    "skew": float(v.skew()) if nun > 2 else 0.0,
                }
            )
            lat = _lattice_check(s)
            if lat.get("on_lattice"):
                entry["lattice"] = lat
                lattice_cols.append(c)
            uni = _uniformity_check(s)
            if uni.get("uniform_like"):
                entry["uniform_like"] = True
                uniform_cols.append(c)
        columns[c] = entry

    dup_rows = int(df.duplicated().sum())
    # near-duplicate rows: quantize numerics to 6 significant digits
    try:
        q = df.copy()
        for c in numeric:
            v = pd.to_numeric(q[c], errors="coerce")
            with np.errstate(divide="ignore", invalid="ignore"):
                mag = np.floor(np.log10(np.abs(v.replace(0, np.nan))))
            q[c] = np.round(v, (5 - mag.fillna(0)).clip(-10, 12).astype(int))
        near_dup = int(q.duplicated().sum())
    except Exception:
        near_dup = dup_rows

    return {
        "n_rows": int(n),
        "n_cols": int(p),
        "numeric_cols": [c for c in numeric],
        "categorical_cols": [c for c in categorical],
        "id_cols": idlike,
        "datetime_cols": dt,
        "constant_cols": constants,
        "duplicate_rows": dup_rows,
        "near_duplicate_rows": near_dup,
        "duplicate_row_frac": round(dup_rows / max(n, 1), 6),
        "lattice_cols": lattice_cols,
        "uniform_sampled_cols": uniform_cols,
        "columns": columns,
    }
