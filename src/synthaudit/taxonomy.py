"""Variable taxonomy — every column gets exactly one primary role."""

from __future__ import annotations

import pandas as pd

ROLES = [
    "target",
    "derived_deterministic",
    "near_deterministic",
    "label_component",
    "leaky_feature",
    "duplicate",
    "constant",
    "identifier",
    "datetime",
    "no_signal",
    "input",
]


def run(
    df: pd.DataFrame, prof: dict, ident: dict, det: dict, leak: dict, target: str | None
) -> dict:
    roles = {}
    derived_set = set(ident.get("derived_columns", []))
    derived = {}
    for f in ident["identities"]:
        m = f.get("derived_member", f["target"])
        if m in derived_set:
            derived[m] = f
    near = {
        f.get("derived_member", f["target"]): f
        for f in ident["identities"]
        if not f.get("exact") and 0.995 <= f.get("r2", 0) < 0.9999
    }
    rules = {r["target"]: r for r in ident["rule_derived_labels"]}
    dup_targets = {
        f.get("derived_member", f["target"])
        for f in ident["identities"]
        if f["type"] == "duplicate_column"
    } & derived_set
    components = set()
    single = {}
    for f in leak.get("findings", []):
        if f["kind"] == "label_components":
            import re

            m = re.findall(r"'([^']+)'", f["detail"])
            components.update(m)
    for f in ident["identities"] + list(rules.values()):
        exactish = f.get("r2", 0) >= 0.9999 or f.get("exact") or f.get("fidelity", 0) >= 0.999
        if not exactish:
            continue  # near-reconstructions flag findings, not roles
        if target and f.get("target") == target:
            components.update(f.get("predictors", []))
        # members of an exact constraint that contains the target are
        # copies/re-expressions of the label -> leaky by construction
        if target and target in f.get("constraint_members", []):
            components.update(c for c in f["constraint_members"] if c != target)
    for s in leak.get("single_feature_screens", []) or []:
        single[s["feature"]] = s["score"]
    det_near = set(det.get("near_deterministic", []) + det.get("deterministic", []))
    descendants = {
        f["target"]
        for f in ident["identities"]
        if target
        and target in f.get("predictors", [])
        and f.get("r2", 0) >= 0.995
        and f["target"] != target
    }

    for c in df.columns:
        if c == target:
            roles[c] = {"role": "target"}
        elif c in prof["constant_cols"]:
            roles[c] = {"role": "constant"}
        elif c in prof["id_cols"]:
            roles[c] = {"role": "identifier"}
        elif c in prof["datetime_cols"]:
            roles[c] = {"role": "datetime"}
        elif c in dup_targets:
            roles[c] = {"role": "duplicate"}
        elif c in components:
            roles[c] = {
                "role": "label_component",
                "why": f"participates in generating rule of '{target}'",
            }
        elif c in derived or c in rules:
            f = derived.get(c) or rules.get(c)
            roles[c] = {"role": "derived_deterministic", "why": f.get("equation", "")[:160]}
        elif c in descendants:
            roles[c] = {"role": "leaky_feature", "why": f"(near-)computed from target '{target}'"}
        elif single.get(c, 0) >= 0.99:
            roles[c] = {
                "role": "leaky_feature",
                "why": f"single-feature score {single[c]:.4f} on target",
            }
        elif c in near or c in det_near:
            f = near.get(c)
            roles[c] = {
                "role": "near_deterministic",
                "why": (f or {}).get("equation", "predictability sweep ≥ 0.98")[:160],
            }
        else:
            roles[c] = {"role": "input"}

    counts = {}
    for v in roles.values():
        counts[v["role"]] = counts.get(v["role"], 0) + 1
    return {"roles": roles, "counts": counts}
