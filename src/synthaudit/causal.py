"""Module 4 — Causal structure scan (advisory).

Deterministic relations violate faithfulness, so derived columns found by
identity mining are removed BEFORE constraint-based discovery (Lemeire et al.
2012; Uhler et al. 2013; Li et al., NeurIPS 2024). The module then runs the
PC algorithm on the reduced stochastic core and reports simulation-artifact
diagnostics (varsortability / R²-sortability, Reisach et al. 2021, 2023)
computed against the recovered graph.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ._util import sample_df

PC_SAMPLE = 4000
PC_MAX_VARS = 14


def _sortability(X: np.ndarray, adj: np.ndarray, values: np.ndarray) -> float:
    """Fraction of directed edges i->j whose 'value' increases along the edge."""
    idx = np.argwhere(adj > 0)
    if len(idx) == 0:
        return float("nan")
    agree = eq = 0
    for i, j in idx:
        if values[j] > values[i]:
            agree += 1
        elif values[j] == values[i]:
            eq += 1
    return float((agree + 0.5 * eq) / len(idx))


def _r2_of_each(X: np.ndarray) -> np.ndarray:
    """R² of each variable regressed on all others (for R²-sortability)."""
    n, p = X.shape
    out = np.zeros(p)
    A = np.column_stack([X, np.ones(n)])
    for j in range(p):
        others = [k for k in range(p) if k != j] + [p]
        beta, *_ = np.linalg.lstsq(A[:, others], X[:, j], rcond=None)
        resid = X[:, j] - A[:, others] @ beta
        v = np.var(X[:, j])
        out[j] = 1 - np.var(resid) / v if v > 0 else 0.0
    return out


def run(df: pd.DataFrame, prof: dict, ident: dict, seed=42) -> dict:
    numeric = [c for c in prof["numeric_cols"] if c not in prof["constant_cols"]]
    derived = set(ident["derived_columns"])
    core = [c for c in numeric if c not in derived]
    excluded = sorted(set(numeric) - set(core))

    out = {
        "excluded_deterministic": excluded,
        "note": (
            "Derived columns removed before discovery: deterministic "
            "relations violate faithfulness and corrupt CI tests."
        ),
    }
    sub = sample_df(df[core].apply(pd.to_numeric, errors="coerce").dropna(), PC_SAMPLE, seed)
    if sub.shape[1] < 3 or len(sub) < 200:
        out["skipped"] = "fewer than 3 stochastic numeric columns"
        return out
    # cap variable count: keep highest-variance-of-rank columns for tractability
    cols = list(sub.columns)
    if len(cols) > PC_MAX_VARS:
        var_rank = sub.std().sort_values(ascending=False)
        cols = list(var_rank.index[:PC_MAX_VARS])
        sub = sub[cols]
        out["variable_cap"] = f"PC run on top-{PC_MAX_VARS} columns by variance"
    X = sub.to_numpy(dtype=float)
    Xs = (X - X.mean(0)) / np.where(X.std(0) > 0, X.std(0), 1.0)

    edges, adj = [], np.zeros((len(cols), len(cols)))
    try:
        from causallearn.search.ConstraintBased.PC import pc

        g = pc(Xs, alpha=0.01, show_progress=False)
        gm = g.G.graph  # -1/1 encoding
        for i in range(len(cols)):
            for j in range(len(cols)):
                if gm[i, j] == -1 and gm[j, i] == 1:  # i --> j
                    edges.append({"from": cols[i], "to": cols[j], "kind": "directed"})
                    adj[i, j] = 1
                elif i < j and gm[i, j] == -1 and gm[j, i] == -1:  # i --- j
                    edges.append({"from": cols[i], "to": cols[j], "kind": "undirected"})
        out["pc_edges"] = edges
        out["pc_n_edges"] = len(edges)
    except Exception as e:  # causal-learn unavailable or failure
        out["pc_error"] = str(e)[:300]

    # simulation-artifact diagnostics on the recovered directed subgraph
    if adj.sum() > 0:
        out["varsortability_est"] = round(_sortability(X, adj, X.var(0)), 4)
        out["r2sortability_est"] = round(_sortability(X, adj, _r2_of_each(Xs)), 4)
        out["sortability_note"] = (
            "Estimated against the PC-recovered graph. Values near 1.0 mean "
            "marginal variance (or R²) increases along recovered edges — the "
            "signature of unstandardized additive-noise simulation (Reisach et "
            "al. 2021): structure learners can 'succeed' by exploiting scale."
        )
    out["stochastic_core"] = cols
    return out
