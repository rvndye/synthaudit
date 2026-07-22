"""SynthAudit orchestrator."""

from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from . import causal, determinism, identity, leakage, profiling, recommend, scoring, taxonomy
from .report import render_html, render_notebook, render_pdf

__all__ = ["Audit"]


class Audit:
    """Audit a synthetic dataset for generator artifacts before ML.

    Parameters
    ----------
    data : pd.DataFrame or path to CSV
    target : optional name of the benchmark target column
    name : display name for reports
    metadata : optional dict for the transparency pillar, e.g.
        {"generator_described": True, "generator_code_available": False,
         "seed_reported": False, "artifacts_disclosed": False}
    test_data : optional held-out split to check train/test contamination
    modules : subset of {"profile","identity","determinism","causal",
        "leakage","taxonomy","scoring","recommend"}; default all
    """

    def __init__(
        self,
        data,
        target=None,
        name="dataset",
        metadata=None,
        test_data=None,
        seed=42,
        modules=None,
        identity_kwargs=None,
    ):
        if isinstance(data, str):
            data = pd.read_csv(data)
        self.df = data
        self.target = target
        self.name = name
        self.metadata = metadata
        self.test_data = test_data
        self.seed = seed
        self.modules = modules
        self.identity_kwargs = identity_kwargs or {}
        self.results: dict = {}

    def run(self, verbose=True) -> dict:
        t0 = time.time()
        mods = self.modules
        run_all = mods is None

        def on(m):
            return run_all or m in mods

        def log(msg):
            if verbose:
                print(f"[synthaudit] {msg}", flush=True)

        log(
            f"auditing '{self.name}' "
            f"({self.df.shape[0]:,} rows x {self.df.shape[1]} cols, "
            f"target={self.target})"
        )
        prof = profiling.profile(self.df)
        self.results["profile"] = prof
        log(
            f"profile: {len(prof['numeric_cols'])} numeric, "
            f"{len(prof['categorical_cols'])} categorical, "
            f"{prof['duplicate_rows']} duplicate rows"
        )

        ident = (
            identity.run(self.df, prof, self.seed, target=self.target, **self.identity_kwargs)
            if on("identity")
            else {
                "identities": [],
                "functional_dependencies": [],
                "rule_derived_labels": [],
                "derived_columns": [],
                "n_exact": 0,
                "n_near": 0,
            }
        )
        self.results["identity"] = ident
        log(
            f"identity mining: {ident['n_exact']} exact, "
            f"{ident['n_near']} near identities, "
            f"{len(ident['functional_dependencies'])} FDs, "
            f"{len(ident['rule_derived_labels'])} rule-derived labels"
        )

        det = (
            determinism.run(
                self.df,
                prof,
                self.seed,
                exclude_predictors=ident["derived_columns"] + prof["constant_cols"],
            )
            if on("determinism")
            else {"sweep": [], "deterministic": [], "near_deterministic": []}
        )
        self.results["determinism"] = det
        log(
            f"determinism sweep: {len(det['deterministic'])} deterministic, "
            f"{len(det['near_deterministic'])} near-deterministic columns"
        )

        cau = causal.run(self.df, prof, ident, self.seed) if on("causal") else {}
        self.results["causal"] = cau
        if cau.get("pc_n_edges") is not None:
            log(
                f"causal scan: {cau['pc_n_edges']} edges on stochastic core "
                f"({len(cau.get('excluded_deterministic', []))} columns excluded)"
            )

        leak = (
            leakage.run(self.df, prof, ident, self.target, self.seed, self.test_data)
            if on("leakage")
            else {"findings": []}
        )
        self.results["leakage"] = leak
        log(
            f"leakage audit: {leak.get('n_critical', 0)} critical, "
            f"{leak.get('n_high', 0)} high findings"
        )

        tax = taxonomy.run(self.df, prof, ident, det, leak, self.target)
        self.results["taxonomy"] = tax

        score = scoring.run(
            self.df,
            prof,
            ident,
            det,
            leak,
            tax,
            self.target,
            metadata=self.metadata,
            seed=self.seed,
        )
        self.results["scoring"] = score
        log(f"BTI = {score['bti']:.3f} (grade {score['grade']}) pillars={score['pillars']}")

        rec = recommend.run(prof, ident, det, leak, tax, score, self.target)
        self.results["recommendations"] = rec
        self.results["meta"] = {
            "name": self.name,
            "target": self.target,
            "n_rows": prof["n_rows"],
            "n_cols": prof["n_cols"],
            "runtime_s": round(time.time() - t0, 2),
            "synthaudit_version": __import__("synthaudit").__version__,
        }
        log(f"done in {self.results['meta']['runtime_s']}s")
        return self.results

    # ----- exports -----
    def generate_report(self, path=None):
        path = path or f"synthaudit_report_{self.name}.html"
        return self.export_html(path)

    def export_html(self, path):
        render_html(self.results, path)
        return path

    def export_pdf(self, path):
        render_pdf(self.results, path)
        return path

    def export_notebook(self, path):
        render_notebook(self.results, self.name, self.target, path)
        return path

    def export_json(self, path):
        def default(o):
            if isinstance(o, (np.integer,)):
                return int(o)
            if isinstance(o, (np.floating,)):
                return float(o)
            if isinstance(o, (np.bool_,)):
                return bool(o)
            if isinstance(o, np.ndarray):
                return o.tolist()
            return str(o)

        with open(path, "w") as fh:
            json.dump(self.results, fh, indent=1, default=default)
        return path

    @property
    def bti(self):
        return self.results.get("scoring", {}).get("bti")
