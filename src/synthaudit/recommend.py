"""Module 7 — Research recommendations."""

from __future__ import annotations


def run(prof, ident, det, leak, taxonomy, scoring, target) -> dict:
    roles = taxonomy["roles"]
    drop = sorted(
        [
            c
            for c, r in roles.items()
            if r["role"]
            in {
                "derived_deterministic",
                "label_component",
                "leaky_feature",
                "duplicate",
                "constant",
            }
        ]
    )
    quarantine = sorted([c for c, r in roles.items() if r["role"] == "near_deterministic"])
    inputs = [c for c, r in roles.items() if r["role"] == "input"]

    # suggest honest prediction targets: predictable but not trivially so
    sweep = {r["column"]: r for r in det.get("sweep", [])}
    suggestions = []
    for c in inputs:
        r = sweep.get(c)
        s = (r or {}).get("skill", (r or {}).get("score"))
        if r and s is not None and 0.3 <= s <= 0.97:
            suggestions.append({"column": c, "oos_score": s, "metric": r["metric"]})
    suggestions.sort(key=lambda s: -s["oos_score"])

    warnings = []
    if any(f["kind"] == "row_order_structure" for f in leak.get("findings", [])):
        warnings.append(
            "Rows are blocked/scheduled: use grouped or temporal "
            "cross-validation, never random K-fold."
        )
    if any(f["kind"] == "duplicate_rows" for f in leak.get("findings", [])):
        warnings.append("Deduplicate before splitting; report scores on the deduplicated view.")
    if scoring["pillars"].get("L") is not None and scoring["pillars"]["L"] < 0.5:
        warnings.append(
            f"Target '{target}' is (near-)derived from shipped "
            f"columns. Any reported model score on it is a claim "
            f"about equation recovery, not about learning."
        )
    if scoring["pillars"].get("I") is not None and scoring["pillars"]["I"] < 0.6:
        warnings.append(
            "Numeric block is strongly rank-deficient: the "
            "generator has low intrinsic dimensionality; feature "
            "importance analyses will be unstable."
        )

    tasks = []
    if target and scoring["pillars"].get("L", 1) and scoring["pillars"]["L"] >= 0.5:
        tasks.append(
            f"Predict '{target}' from the recommended feature view ({len(inputs)} input columns)."
        )
    for s in suggestions[:3]:
        tasks.append(
            f"Predict '{s['column']}' (honest out-of-sample {s['metric']}≈{s['oos_score']:.2f})."
        )
    if not tasks:
        tasks.append(
            "No non-trivial supervised task survives the audit; "
            "consider this dataset for pipeline testing only."
        )

    return {
        "drop_columns": drop,
        "quarantine_columns": quarantine,
        "recommended_feature_view": sorted(inputs),
        "suggested_targets": suggestions[:5],
        "suggested_tasks": tasks,
        "protocol_warnings": warnings,
    }
