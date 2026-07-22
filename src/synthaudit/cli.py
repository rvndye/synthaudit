"""SynthAudit command-line interface.

Examples
--------
synthaudit audit data.csv --target label --html report.html
synthaudit audit train.csv --target y --test-data test.csv --fail-below C
synthaudit selftest --extended
synthaudit version
"""

from __future__ import annotations

import argparse
import json
import sys

GRADE_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}


def _parse_metadata(pairs):
    if not pairs:
        return None
    truthy = {"1", "true", "yes", "y"}
    out = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"--metadata expects KEY=VALUE, got: {pair!r}")
        k, v = pair.split("=", 1)
        out[k.strip()] = v.strip().lower() in truthy
    return out


def _cmd_audit(args) -> int:
    import pandas as pd

    from .audit import Audit

    df = pd.read_csv(args.data)
    name = args.name or args.data.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    test_df = pd.read_csv(args.test_data) if args.test_data else None
    audit = Audit(
        df,
        target=args.target,
        name=name,
        metadata=_parse_metadata(args.metadata),
        test_data=test_df,
        seed=args.seed,
    )
    results = audit.run(verbose=not args.quiet)

    if args.html:
        audit.export_html(args.html)
    if args.pdf:
        audit.export_pdf(args.pdf)
    if args.json:
        audit.export_json(args.json)
    if args.notebook:
        audit.export_notebook(args.notebook)

    score = results["scoring"]
    summary = {
        "dataset": name,
        "target": args.target,
        "bti": score["bti"],
        "grade": score["grade"],
        "pillars": score["pillars"],
        "critical_findings": results["leakage"].get("n_critical", 0),
        "exact_relations": results["identity"]["n_exact"],
    }
    print(json.dumps(summary, indent=2))

    if args.fail_below:
        want = GRADE_ORDER[args.fail_below.upper()]
        got = GRADE_ORDER[score["grade"]]
        if got < want:
            print(
                f"synthaudit: grade {score['grade']} is below the required "
                f"{args.fail_below.upper()}; failing.",
                file=sys.stderr,
            )
            return 1
    return 0


def _cmd_selftest(args) -> int:
    from .audit import Audit
    from .testbed import make_planted, score_detection

    df, truth = make_planted(n=args.n, seed=args.seed, extended=args.extended)
    audit = Audit(df, target="target_y", name="selftest")
    results = audit.run(verbose=not args.quiet)
    sc = score_detection(results, truth)
    print(
        json.dumps(
            {
                "planted_detected": f"{sc['n_detected']}/{sc['n_planted']}",
                "recall": sc["recall"],
                "negative_control_pass": sc["negative_control_pass"],
            },
            indent=2,
        )
    )
    ok = sc["recall"] == 1.0 and sc["negative_control_pass"] == 1.0
    if not ok:
        print("synthaudit: self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def _cmd_version(_args) -> int:
    from . import __version__

    print(__version__)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="synthaudit",
        description=("Audit synthetic datasets for generator artifacts before machine learning."),
    )
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("audit", help="audit a CSV file and export reports")
    a.add_argument("data", help="path to the CSV file to audit")
    a.add_argument("--target", help="benchmark target column")
    a.add_argument("--name", help="display name (default: file stem)")
    a.add_argument("--test-data", help="optional held-out CSV for contamination checks")
    a.add_argument(
        "--metadata",
        action="append",
        metavar="KEY=VAL",
        help=(
            "transparency metadata, repeatable (keys: generator_described, "
            "generator_code_available, seed_reported, artifacts_disclosed)"
        ),
    )
    a.add_argument("--html", help="write self-contained HTML report here")
    a.add_argument("--pdf", help="write one-page PDF scorecard here")
    a.add_argument("--json", help="write machine-readable findings here")
    a.add_argument("--notebook", help="write reproduction notebook here")
    a.add_argument("--seed", type=int, default=42)
    a.add_argument(
        "--fail-below",
        choices=["A", "B", "C", "D", "a", "b", "c", "d"],
        help="exit nonzero if the grade is below this (CI gate)",
    )
    a.add_argument("--quiet", action="store_true", help="suppress progress lines")
    a.set_defaults(func=_cmd_audit)

    s = sub.add_parser("selftest", help="run the planted-artifact self-validation")
    s.add_argument("--extended", action="store_true", help="include the out-of-class artifact")
    s.add_argument("--n", type=int, default=20000)
    s.add_argument("--seed", type=int, default=42)
    s.add_argument("--quiet", action="store_true")
    s.set_defaults(func=_cmd_selftest)

    v = sub.add_parser("version", help="print the installed version")
    v.set_defaults(func=_cmd_version)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
