"""Module 2 — Identity mining.

Recovers exact and near-exact generator equations:
  * linear identities        y = a·x + c           (per-column OLS + sparsification)
  * sum/balance constraints  Σ a_i x_i + c = 0     (special case of the above)
  * power-law identities     y = C · Π x_i^{a_i}   (OLS in log space)
  * regime-affine identities y = f(x) + offset(cat) (linear + categorical offsets)
  * functional dependencies  A → B                 (partition refinement, g3 error)
  * rule-derived labels      y = rules(x)          (shallow-tree fidelity + extraction)
  * threshold derivations    y = 1{x > t}          (perfect univariate splits)
  * duplicate columns        y ≡ x                 (up to jitter)
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text

from ._util import EXACT_R2, NEAR_R2, RULE_FIDELITY, fmt_equation, sample_df

MAX_LIN_COLS = 120
FIT_SAMPLE = 25000
VERIFY_SAMPLE = 200000


class _GramMiner:
    """Minimal-support linear identity mining from one Gram matrix.

    Build G = [X, 1]'[X, 1] once; every subset OLS then costs O(|S|^3),
    which makes greedy backward elimination (for MINIMAL supports) cheap.
    Minimality matters: with collinear derived columns present, plain OLS
    returns arbitrary supports that pollute the recovered constraint set.
    """

    def __init__(self, X: np.ndarray):
        n, p = X.shape
        self.n, self.p = n, p
        A = np.column_stack([X, np.ones(n)])
        self.G = A.T @ A
        self.stds = X.std(axis=0)

    def fit(self, S, j):
        idx = list(S) + [self.p]
        Gs = self.G[np.ix_(idx, idx)]
        cs = self.G[idx, j]
        try:
            beta, *_ = np.linalg.lstsq(Gs, cs, rcond=None)
        except np.linalg.LinAlgError:  # SVD non-convergence on wild scales
            beta = np.linalg.solve(
                Gs + 1e-8 * np.trace(Gs) / max(len(idx), 1) * np.eye(len(idx)), cs
            )
        rss = float(self.G[j, j] - 2 * beta @ cs + beta @ Gs @ beta)
        return beta, max(rss, 0.0) / self.n

    def minimal_identity(self, j, near_r2=NEAR_R2, max_support=8):
        vy = self.G[j, j] / self.n - (self.G[j, self.p] / self.n) ** 2
        if vy <= 1e-300:
            return None
        S = [k for k in range(self.p) if k != j]
        beta, mse = self.fit(S, j)
        r2 = 1 - mse / vy
        if r2 < near_r2:
            return None
        keep_thr = EXACT_R2 if r2 >= EXACT_R2 else near_r2
        improved = True
        while improved and len(S) > 1:
            improved = False
            contrib = np.abs(beta[: len(S)]) * self.stds[S]
            for k in np.argsort(contrib):
                S2 = [s for i, s in enumerate(S) if i != int(k)]
                beta2, mse2 = self.fit(S2, j)
                if 1 - mse2 / vy >= keep_thr:
                    S, beta, mse = S2, beta2, mse2
                    improved = True
                    break
        r2 = 1 - mse / vy
        if len(S) > max_support:
            return None
        return S, beta, float(min(r2, 1.0)), float(np.sqrt(max(mse, 0.0)))


def _verify_full(df, cols, yname, support_names, coefs, intercept, space):
    """Re-validate a mined identity on ALL rows; returns (r2, max_abs_resid)."""
    try:
        use = support_names + [yname]
        M = df[use].apply(pd.to_numeric, errors="coerce")
        M = M.replace([np.inf, -np.inf], np.nan).dropna()
        if space == "log":
            M = M[(M > 0).all(axis=1)]
            M = np.log(M)
        y = M[yname].to_numpy(dtype=float)
        pred = np.full(len(M), intercept, dtype=float)
        for nm in support_names:
            pred += coefs[nm] * M[nm].to_numpy(dtype=float)
        resid = y - pred
        vy = np.var(y)
        r2 = 1 - np.var(resid) / vy if vy > 0 else 0.0
        return float(min(r2, 1.0)), float(np.max(np.abs(resid)))
    except Exception:
        return None, None


def mine_linear(df: pd.DataFrame, numeric_cols, seed=42) -> list[dict]:
    """Per-column minimal OLS identities over the numeric block, raw + log."""
    cols = [c for c in numeric_cols if df[c].nunique(dropna=True) > 1][:MAX_LIN_COLS]
    if len(cols) < 2:
        return []
    sub = sample_df(df[cols].apply(pd.to_numeric, errors="coerce"), FIT_SAMPLE, seed)
    sub = sub.replace([np.inf, -np.inf], np.nan).dropna()
    if len(sub) < 50:
        return []
    X = sub.to_numpy(dtype=float)
    found = []

    def emit(res, names, yname, space):
        S, beta, r2, rsd = res
        coefs = {names[s]: float(b) for s, b in zip(S, beta[: len(S)], strict=False)}
        intercept = float(beta[-1])
        r2f, maxres = _verify_full(df, cols, yname, list(coefs), coefs, intercept, space)
        if r2f is not None and r2f < NEAR_R2:
            return None  # sample fit did not survive full-data verification
        return {
            "type": "linear" if space == "raw" else "power_law",
            "target": yname,
            "predictors": list(coefs),
            "coefficients": coefs,
            "intercept": intercept,
            "r2": float(r2f if r2f is not None else r2),
            "residual_sd": rsd,
            "max_abs_residual_full": maxres,
            "exact": bool((r2f if r2f is not None else r2) >= EXACT_R2),
            "equation": fmt_equation(
                yname, coefs, intercept, "linear" if space == "raw" else "loglinear"
            ),
        }

    miner = _GramMiner(X)
    for j, yname in enumerate(cols):
        res = miner.minimal_identity(j)
        if res:
            out = emit(res, cols, yname, "raw")
            if out:
                found.append(out)
    # log space (positive columns only)
    pos = [j for j, c in enumerate(cols) if (sub[c] > 0).all()]
    if len(pos) >= 2:
        L = np.log(X[:, pos])
        pnames = [cols[j] for j in pos]
        already = {f["target"] for f in found if f["exact"]}
        lminer = _GramMiner(L)
        for jj, yname in enumerate(pnames):
            if yname in already:
                continue
            res = lminer.minimal_identity(jj)
            if res:
                out = emit(res, pnames, yname, "log")
                if out:
                    found.append(out)
    return found


def mine_regime_affine(
    df: pd.DataFrame, numeric_cols, categorical_cols, linear_found, seed=42
) -> list[dict]:
    """y = linear(x) + offset(level), via fixed-effects (within) demeaning:
    demean y and X by category level, run minimal identity mining in the
    demeaned space, then recover per-level offsets."""
    out = []
    already = {f["target"] for f in linear_found if f["exact"]}
    cats = [
        c
        for c in categorical_cols
        if not pd.api.types.is_numeric_dtype(df[c]) or df[c].nunique() <= 12
    ]
    cols = [c for c in numeric_cols if c not in already and df[c].nunique() > 1][:60]
    if not cats or len(cols) < 2:
        return out
    sub = sample_df(df, FIT_SAMPLE, seed)
    num = sub[cols].apply(pd.to_numeric, errors="coerce")
    num = num.replace([np.inf, -np.inf], np.nan)
    keep = num.dropna().index
    num = num.loc[keep]
    if len(num) < 100:
        return out
    claimed = set()
    for cat in cats:
        g = sub.loc[keep, cat].astype(str)
        if g.nunique() < 2 or g.nunique() > 12:
            continue
        dem = num.groupby(g).transform(lambda v: v - v.mean())
        Xd = dem.to_numpy(dtype=float)
        miner = _GramMiner(Xd)
        for j, yname in enumerate(cols):
            if yname in claimed:
                continue
            vy_raw = float(num[yname].var())
            vd = float(dem[yname].var())
            if vy_raw <= 0 or vd <= 1e-300:
                continue
            res = miner.minimal_identity(j)
            if not res:
                continue
            S, beta, r2_within, rsd = res
            names = [cols[s] for s in S]
            # recover offsets on the raw scale and validate overall fit
            pred = num[names].to_numpy(dtype=float) @ beta[: len(S)]
            resid_raw = num[yname].to_numpy(dtype=float) - pred
            offsets = pd.Series(resid_raw, index=keep).groupby(g).mean()
            final = resid_raw - offsets.reindex(g).to_numpy()
            r2c = 1 - np.var(final) / vy_raw
            if r2c < NEAR_R2:
                continue
            # skip if a plain linear identity already explains it (no regime)
            plain = 1 - np.var(resid_raw - resid_raw.mean()) / vy_raw
            if plain >= r2c - 1e-6 or offsets.std() < 1e-9:
                continue
            coefs = {nm: float(b) for nm, b in zip(names, beta[: len(S)], strict=False)}
            claimed.add(yname)
            out.append(
                {
                    "type": "regime_affine",
                    "target": yname,
                    "predictors": names,
                    "coefficients": coefs,
                    "regime_variable": cat,
                    "offsets_by_level": {str(k): round(float(v), 6) for k, v in offsets.items()},
                    "r2": float(min(r2c, 1.0)),
                    "residual_sd": float(np.std(final)),
                    "exact": bool(r2c >= EXACT_R2),
                    "equation": (
                        f"{yname} = "
                        + " + ".join(f"{v:g}*{k}" for k, v in coefs.items())
                        + f" + offset({cat})"
                    ),
                }
            )
    return out


def mine_functional_dependencies(
    df: pd.DataFrame, categorical_cols, id_cols, max_card=2000, seed=42
) -> list[dict]:
    """Single-determinant FDs A→B with g3 violation rate, on discrete-ish columns."""
    n = len(df)
    cand = []
    for c in df.columns:
        nun = df[c].nunique(dropna=True)
        if 1 < nun <= max_card and nun < 0.6 * n:
            cand.append(c)
    cand = cand[:40]
    out = []
    sub = sample_df(df[cand], 60000, seed) if cand else df
    for a, b in itertools.permutations(cand, 2):
        if a in id_cols:
            continue
        na, nb = sub[a].nunique(dropna=True), sub[b].nunique(dropna=True)
        if na >= 0.5 * len(sub) or na < 2:
            continue  # near-key determinants are trivial
        # dependent non-degeneracy: an FD onto a >98%-constant column merely
        # restates class imbalance (cf. the rule-label guard) and is noise
        modal_b = sub[b].value_counts(dropna=False, normalize=True).iloc[0]
        if modal_b > 0.98:
            continue
        grp = sub.groupby(a, dropna=False, observed=True)[b]
        modal = grp.agg(lambda s: s.value_counts(dropna=False).iloc[0] if len(s) else 0)
        g3 = 1.0 - modal.sum() / max(len(sub), 1)
        if g3 <= 0.005:
            out.append(
                {
                    "type": "functional_dependency",
                    "determinant": a,
                    "dependent": b,
                    "g3_violation_rate": round(float(g3), 6),
                    "exact": bool(g3 == 0.0),
                    "determinant_cardinality": int(na),
                    "dependent_cardinality": int(nb),
                    "equation": f"{a} -> {b}",
                }
            )
    # drop symmetric pairs (bijections) duplicated both ways; keep both but mark
    return out


def mine_rule_labels(
    df: pd.DataFrame, categorical_cols, numeric_cols, max_depth=5, seed=42
) -> list[dict]:
    """Shallow-tree fidelity test: is a discrete column a rule of other columns?"""
    out = []
    targets = [c for c in df.columns if df[c].nunique(dropna=True) in range(2, 21)]
    for t in targets:
        feats = [c for c in numeric_cols if c != t and df[c].nunique() > 1]
        feats += [
            c for c in categorical_cols if c != t and c not in feats and df[c].nunique() <= 32
        ]
        feats = feats[:60]
        if not feats:
            continue
        sub = sample_df(df[feats + [t]].dropna(subset=[t]), 60000, seed)
        X = pd.DataFrame(index=sub.index)
        for c in feats:
            if pd.api.types.is_numeric_dtype(sub[c]):
                X[c] = pd.to_numeric(sub[c], errors="coerce")
            else:
                X[c] = sub[c].astype("category").cat.codes
        X = X.replace([np.inf, -np.inf], np.nan).fillna(X.median())
        y = sub[t].astype(str).to_numpy()
        base = pd.Series(y).value_counts(normalize=True).iloc[0]
        for depth in (2, max_depth):
            tree = DecisionTreeClassifier(max_depth=depth, random_state=seed)
            tree.fit(X, y)
            fid = tree.score(X, y)
            # a fidelity that merely restates extreme class imbalance is not a
            # derivation: require the rule to remove >=50% of the majority
            # error, and on >99.5%-constant columns accept only perfect rules
            if fid < RULE_FIDELITY:
                continue
            if (1 - fid) > 0.5 * (1 - base):
                continue
            if base > 0.995 and fid < 1.0:
                continue
            if True:
                used = [
                    X.columns[i]
                    for i in np.argsort(tree.feature_importances_)[::-1]
                    if tree.feature_importances_[i] > 0
                ]
                n_viol = int(round((1 - fid) * len(y)))
                out.append(
                    {
                        "type": "rule_derived_label",
                        "target": t,
                        "predictors": used,
                        "tree_depth": depth,
                        "fidelity": round(float(fid), 6),
                        "violating_rows_in_sample": n_viol,
                        "majority_baseline": round(float(base), 4),
                        "rules": export_text(tree, feature_names=list(X.columns), max_depth=depth)[
                            :4000
                        ],
                        "exact": bool(fid == 1.0),
                        "equation": f"{t} = decision_rules({', '.join(used[:6])})",
                    }
                )
                break
    return out


def mine_threshold_derivations(df: pd.DataFrame, numeric_cols, seed=42) -> list[dict]:
    """Binary column == 1{numeric > t}: perfect univariate splits (sign labels)."""
    out = []
    bins = [c for c in df.columns if df[c].nunique(dropna=True) == 2]
    nums = [c for c in numeric_cols if df[c].nunique() > 10]
    if not bins or not nums:
        return out
    sub = sample_df(df, 60000, seed)
    for b in bins:
        yb = sub[b]
        classes = yb.dropna().unique()
        y = (yb == classes[0]).to_numpy()
        if min(y.sum(), (~y).sum()) < 20:
            continue  # vacuous splits on ultra-rare classes are not derivations
        for x in nums:
            if x == b:
                continue
            v = pd.to_numeric(sub[x], errors="coerce").to_numpy()
            ok = ~np.isnan(v)
            if ok.sum() < 100:
                continue
            vv, yy = v[ok], y[ok]
            lo0, hi0 = (
                vv[~yy].max() if (~yy).any() else -np.inf,
                vv[~yy].min() if (~yy).any() else np.inf,
            )
            lo1, hi1 = vv[yy].max() if yy.any() else -np.inf, vv[yy].min() if yy.any() else np.inf
            # perfect split exists iff class ranges do not overlap
            if hi1 > lo0 or hi0 > lo1:
                sep = None
                if lo0 < hi1:  # class0 entirely below class1
                    sep = (lo0 + hi1) / 2
                    rule = f"{b} == '{classes[0]}'  iff  {x} > {sep:.6g}"
                elif lo1 < hi0:  # class1 entirely below class0
                    sep = (lo1 + hi0) / 2
                    rule = f"{b} == '{classes[0]}'  iff  {x} <= {sep:.6g}"
                if sep is not None and np.isfinite(sep):
                    out.append(
                        {
                            "type": "threshold_derivation",
                            "target": b,
                            "predictors": [x],
                            "threshold": float(sep),
                            "exact": True,
                            "r2": 1.0,
                            "equation": rule,
                        }
                    )
                    break
    return out


def mine_duplicate_columns(df: pd.DataFrame, numeric_cols) -> list[dict]:
    out = []
    cols = [c for c in numeric_cols if df[c].nunique() > 1][:MAX_LIN_COLS]
    if len(cols) < 2:
        return out
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    sub = sub.replace([np.inf, -np.inf], np.nan).dropna()
    if len(sub) < 50:
        return out
    corr = np.corrcoef(sub.to_numpy(dtype=float), rowvar=False)
    for i, j in itertools.combinations(range(len(cols)), 2):
        r = corr[i, j]
        if np.isfinite(r) and abs(r) > 0.9999:
            out.append(
                {
                    "type": "duplicate_column",
                    "target": cols[j],
                    "predictors": [cols[i]],
                    "corr": round(float(r), 8),
                    "exact": bool(abs(r) > 1 - 1e-9),
                    "equation": f"{cols[j]} ≈ {'+' if r > 0 else '-'}{cols[i]} (|r|={abs(r):.6f})",
                }
            )
    # identical non-numeric columns
    other = [c for c in df.columns if c not in cols]
    for a, b in itertools.combinations(other, 2):
        try:
            if df[a].astype(str).equals(df[b].astype(str)):
                out.append(
                    {
                        "type": "duplicate_column",
                        "target": b,
                        "predictors": [a],
                        "corr": 1.0,
                        "exact": True,
                        "equation": f"{b} == {a}",
                    }
                )
        except Exception:
            continue
    return out


def _collapse(identities: list[dict], df_cols, audit_target=None) -> list[dict]:
    """Collapse symmetric re-arrangements of one constraint into one finding.

    An exact relation among k variables yields up to k per-column identities
    (s4 = -(s1+s2+s3) is also s1 = -(s2+s3+s4), ...). We group exact
    linear/power/duplicate findings by their variable set and keep a single
    canonical form, electing one 'derived member' per constraint: the last
    column in dataframe order, never the audit target (the generator's own
    output ordering is the best available prior; the audit target is the
    object of study, so a shipped copy of it is the derived artifact).
    """
    order = {c: i for i, c in enumerate(df_cols)}
    groups: dict[frozenset, list] = {}
    keep = []
    for f in identities:
        symmetric = (
            f["type"] in ("linear", "power_law", "regime_affine") and f.get("r2", 0) >= 0.9999
        ) or (f["type"] == "duplicate_column" and abs(f.get("corr", 0)) > 0.9999)
        if symmetric:
            key = frozenset([f["target"], *f["predictors"]])
            groups.setdefault(key, []).append(f)
        else:
            keep.append(f)

    for key, fs in groups.items():
        members = sorted(key, key=lambda c: order.get(c, 10**9))
        cands = [c for c in members if c != audit_target] or members
        derived = cands[-1]
        matching = [f for f in fs if f["target"] == derived]
        pref = {"linear": 0, "power_law": 1, "duplicate_column": 2}
        matching.sort(key=lambda f: pref.get(f["type"], 9))
        if matching:
            chosen = dict(matching[0])
        else:
            chosen = dict(sorted(fs, key=lambda f: pref.get(f["type"], 9))[0])
            if chosen["type"] == "duplicate_column":
                pair = [chosen["target"], *chosen["predictors"]]
                src = [c for c in pair if c != derived][0]
                chosen.update(
                    target=derived, predictors=[src], equation=f"{derived} ≈ copy of {src}"
                )
            else:
                chosen["note"] = "symmetric constraint; derived member elected by column order"
        chosen["constraint_members"] = members
        chosen["derived_member"] = derived
        # relabel a unit-coefficient single-predictor identity as a duplicate
        if (
            chosen["type"] == "linear"
            and len(chosen.get("predictors", [])) == 1
            and chosen.get("coefficients")
        ):
            coef = list(chosen["coefficients"].values())[0]
            if abs(abs(coef) - 1) < 1e-6:
                chosen["type"] = "duplicate_column"
        keep.append(chosen)
    return keep


def _disposition(f: dict, target) -> str:
    """Classify a recovered relation for the false-positive discussion:
    deterministic structure involving the target is benchmark leakage;
    structure among non-target columns is a (possibly legitimate) structural
    constraint — physics, accounting, or export redundancy — that harms
    ML analyses through rank deficiency, not through answer-key leakage."""
    members = set(f.get("constraint_members", [f.get("target"), *f.get("predictors", [])]))
    if target and target in members:
        return "target_leakage"
    if f["type"] == "duplicate_column":
        return "redundancy"
    return "structural_constraint"


def run(
    df: pd.DataFrame, prof: dict, seed=42, target=None, max_rounds: int = 5, mine_fds: bool = True
) -> dict:
    """Iterative peeling: mine exact constraints, elect one derived member per
    constraint, remove it, and re-mine. A single pass cannot resolve chained
    derivations (a duplicate of x also re-expresses every identity that x
    participates in); peeling converges to a stable set of derived columns
    and a minimal constraint list."""
    numeric = [c for c in prof["numeric_cols"] if c not in prof["constant_cols"]]
    cats = prof["categorical_cols"]
    ids = prof["id_cols"]

    removed: set = set()
    exact_identities: list[dict] = []
    near_identities: list[dict] = []
    for _ in range(max_rounds):
        active = [c for c in numeric if c not in removed]
        if len(active) < 2:
            break
        lin = mine_linear(df, active, seed)
        reg = mine_regime_affine(df, active, cats, lin, seed)
        dups = mine_duplicate_columns(df, active)
        cand = _collapse(lin + reg + dups, list(df.columns), target)

        def _fit(f):
            return (
                abs(f.get("corr", 0))
                if f["type"] == "duplicate_column" and "r2" not in f
                else f.get("r2", 0)
            )

        new_exact = [f for f in cand if _fit(f) >= 0.9999]
        if not new_exact:
            near_identities = [f for f in cand if 0.995 <= _fit(f) < 0.9999]
            break
        # simplest constraints first; if two groups elect the same derived
        # member they are entangled — record one, re-mine the rest next round
        new_exact.sort(key=lambda f: len(f.get("constraint_members", [1, 2])))
        this_round = set()
        for f in new_exact:
            m = f.get("derived_member", f["target"])
            if m in this_round:
                continue
            this_round.add(m)
            exact_identities.append(f)
        removed |= this_round

    # discrete-label derivations are mined once against the FULL column set:
    # a label derived from a shipped (even derived) column is still leakage
    thresh = mine_threshold_derivations(df, numeric, seed)
    rules = mine_rule_labels(df, cats, numeric, seed=seed)
    rules = [
        r
        for r in rules  # threshold form is crisper than a tree
        if r["target"] not in {t["target"] for t in thresh}
    ]
    fds = mine_functional_dependencies(df, cats, ids, seed=seed) if mine_fds else []

    identities = exact_identities + near_identities + thresh
    for f in identities:
        f["disposition"] = _disposition(f, target)
    for r in rules:
        r["disposition"] = "target_leakage" if r["target"] == target else "structural_constraint"
    n_exact = sum(1 for f in identities + fds + rules if f.get("exact"))
    derived = set(removed)
    derived |= {r["target"] for r in rules if r["fidelity"] >= RULE_FIDELITY}
    derived |= {t["target"] for t in thresh}
    derived.discard(target)
    return {
        "identities": identities,
        "functional_dependencies": fds,
        "rule_derived_labels": rules,
        "n_exact": n_exact,
        "n_near": len(near_identities),
        "derived_columns": sorted(derived),
        "peeling_rounds": len(exact_identities) and len(removed) or 0,
    }
