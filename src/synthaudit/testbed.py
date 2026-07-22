"""Planted-artifact validation testbed.

Generates a dataset with KNOWN generator artifacts and returns the ground
truth, so the auditor's detection precision/recall can be measured.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def truth_roles(extended: bool = False) -> dict:
    """Acceptable taxonomy roles per column (for role-accuracy metrics)."""
    roles = {
        **{
            c: {"input"}
            for c in ["x1", "x2", "x3", "x4", "x5", "x6", "x7", "s1", "s2", "s3", "regime"]
        },
        # stab_score is honestly near-deterministic from inputs (tanh + small
        # noise), so either role is a correct description
        "stab_score": {"input", "near_deterministic"},
        "noise_col": {"input", "no_signal"},
        "lin_exact": {"derived_deterministic"},
        "power_law": {"derived_deterministic"},
        "regime_eff": {"derived_deterministic"},
        "s4": {"derived_deterministic"},
        "sign_label": {"derived_deterministic"},
        "thresh_flag": {"derived_deterministic"},
        "dup_x1": {"duplicate", "derived_deterministic"},
        "leak_copy": {"duplicate", "leaky_feature", "label_component"},
        "post_outcome": {"leaky_feature", "near_deterministic"},
        "const_col": {"constant"},
        "target_y": {"target"},
    }
    if extended:
        roles["nl_deriv"] = {"near_deterministic", "derived_deterministic"}
    return roles


def role_accuracy(results: dict, extended: bool = False) -> float:
    """Fraction of columns assigned an acceptable role."""
    want = truth_roles(extended)
    got = results["taxonomy"]["roles"]
    hits = sum(1 for c, ok in want.items() if got.get(c, {}).get("role") in ok)
    return round(hits / len(want), 4)


def make_planted(n: int = 20000, seed: int = 42, extended: bool = False):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(2, 1.5, n)
    x3 = rng.uniform(0.5, 3, n)
    x4 = rng.exponential(1, n) + 0.1
    x5 = rng.uniform(1, 4, n)
    x6 = rng.normal(5, 2, n)
    x7 = rng.normal(0, 1, n)
    s1, s2, s3 = rng.normal(0, 1, n), rng.normal(0, 1, n), rng.normal(0, 1, n)
    c = rng.choice(["A", "B", "C"], n, p=[0.5, 0.3, 0.2])
    base = np.select([c == "A", c == "B", c == "C"], [1.0, 1.045, 0.98])

    lin = 3 * x1 - 2 * x2 + 5  # A1 exact linear
    s4 = -(s1 + s2 + s3)  # A2 balance constraint
    pw = 2.5 * x3**2 * x4 / np.sqrt(x5)  # A3 power law
    reg = base - 0.015 * x6  # A4 regime affine
    flag = ((x1 > 1.0) & (x4 < 0.8)).astype(int)  # A5 threshold rule
    stab = np.tanh(0.8 * x1 - 0.5 * x3 + 0.3 * x6 - 1.5) + rng.normal(0, 0.05, n)
    sign_label = np.where(stab > 0, "unstable", "stable")  # A6 sign derivation
    noise = rng.normal(0, 1, n)  # N1 pure noise (negative ctrl)
    const = np.full(n, 7.0)  # A7 constant
    dup = x1 + rng.normal(0, 1e-9, n)  # A8 duplicate column
    y = 2 * np.sin(x1) + 0.5 * x2 * x3 + rng.normal(0, 0.3, n)  # honest target
    leaky = y + rng.normal(0, 1e-6, n)  # A9 target near-copy
    post = 0.85 * y + 0.15 * x6 + rng.normal(0, 0.05, n)  # A10 post-outcome feature

    df = pd.DataFrame(
        {
            "x1": x1,
            "x2": x2,
            "x3": x3,
            "x4": x4,
            "x5": x5,
            "x6": x6,
            "x7": x7,
            "s1": s1,
            "s2": s2,
            "s3": s3,
            "s4": s4,
            "regime": c,
            "lin_exact": lin,
            "power_law": pw,
            "regime_eff": reg,
            "thresh_flag": flag,
            "stab_score": stab,
            "sign_label": sign_label,
            "noise_col": noise,
            "const_col": const,
            "dup_x1": dup,
            "post_outcome": post,
            "leak_copy": leaky,
            "target_y": y,
        }
    )
    if extended:
        # A11: nonlinear derived column OUTSIDE the identity miner's function
        # classes — only the determinism sweep can catch it (ablation probe)
        df["nl_deriv"] = np.sin(x1) * x3**2 + rng.normal(0, 0.05, n)

    truth = {
        "A1_linear": {"column": "lin_exact", "kind": "linear"},
        "A2_balance": {"column": "s4", "kind": "linear"},
        "A3_powerlaw": {"column": "power_law", "kind": "power_law"},
        "A4_regime": {"column": "regime_eff", "kind": "regime_affine"},
        "A5_rule": {"column": "thresh_flag", "kind": "rule_or_threshold"},
        "A6_sign": {"column": "sign_label", "kind": "rule_or_threshold"},
        "A7_constant": {"column": "const_col", "kind": "constant"},
        "A8_duplicate": {"column": "dup_x1", "kind": "duplicate"},
        "A9_leak": {"column": "leak_copy", "kind": "target_leak"},
        "A10_post": {"column": "post_outcome", "kind": "single_feature_flag"},
        # negative controls: must NOT be flagged as exact-deterministic
        "N1_noise": {"column": "noise_col", "kind": "none"},
        "N2_exogenous": {"column": "x1", "kind": "none"},
        "N3_target": {"column": "target_y", "kind": "none"},
    }
    if extended:
        truth["A11_nonlinear"] = {"column": "nl_deriv", "kind": "nonlinear_near_det"}
    return df, truth


def score_detection(results: dict, truth: dict) -> dict:
    """Compare audit results with planted ground truth."""
    ident = results["identity"]
    prof = results["profile"]
    leak = results["leakage"]
    tax = results["taxonomy"]["roles"]

    def in_constraint(col, types=None, min_r2=0.9999):
        for f in ident["identities"]:
            if types and f["type"] not in types:
                continue
            fit = max(abs(f.get("corr", 0) or 0), f.get("r2", 0) or 0)
            members = f.get("constraint_members", [f["target"], *f.get("predictors", [])])
            if col in members and fit >= min_r2:
                return True
        return False

    rule_targets = {r["target"] for r in ident["rule_derived_labels"]}
    thresh_targets = {
        f["target"] for f in ident["identities"] if f["type"] == "threshold_derivation"
    }
    single_flags = {
        s["feature"] for s in (leak.get("single_feature_screens") or []) if s["score"] >= 0.95
    }

    rows = []
    for aid, spec in truth.items():
        col, kind = spec["column"], spec["kind"]
        if kind == "linear":
            hit = in_constraint(col, ("linear",))
        elif kind == "power_law":
            hit = in_constraint(col, ("power_law", "linear"), 0.999)
        elif kind == "regime_affine":
            hit = any(f["target"] == col and f.get("r2", 0) >= 0.995 for f in ident["identities"])
        elif kind == "rule_or_threshold":
            hit = col in rule_targets or col in thresh_targets
        elif kind == "constant":
            hit = col in prof["constant_cols"]
        elif kind == "duplicate":
            hit = in_constraint(col, ("duplicate_column", "linear")) and tax.get(col, {}).get(
                "role"
            ) in {"duplicate", "derived_deterministic"}
        elif kind == "target_leak":
            hit = col in single_flags or in_constraint(col)
        elif kind == "single_feature_flag":
            hit = col in single_flags
        elif kind == "nonlinear_near_det":
            sweep = {
                r["column"]: r["class"] for r in results.get("determinism", {}).get("sweep", [])
            }
            hit = (
                sweep.get(col) in {"deterministic", "near_deterministic"}
                or tax.get(col, {}).get("role") == "near_deterministic"
            )
        elif kind == "none":  # negative control: role must stay input/target
            hit = tax.get(col, {}).get("role") in {"input", "target"}
        rows.append(
            {
                "artifact": aid,
                "column": col,
                "kind": kind,
                "detected" if kind != "none" else "clean": bool(hit),
            }
        )

    pos = [r for r in rows if r["kind"] != "none"]
    neg = [r for r in rows if r["kind"] == "none"]
    tp = sum(r["detected"] for r in pos)
    tn = sum(r["clean"] for r in neg)
    return {
        "rows": rows,
        "recall": round(tp / len(pos), 4),
        "negative_control_pass": round(tn / len(neg), 4),
        "n_planted": len(pos),
        "n_detected": tp,
    }
