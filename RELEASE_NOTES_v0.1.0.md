## SynthAudit 0.1.0

First public release, accompanying the SynthAudit methodology paper (under
submission at JMLR).

**SynthAudit audits released synthetic tabular datasets for generator
artifacts before machine learning**, with no access to the real source data
and no access to the generator: it recovers equations, rule- and
threshold-derived labels, functional dependencies, schedule leakage, and
train/test contamination; classifies every column; separates benchmark
leakage from legitimate physical structure; and scores each release with a
decomposable Benchmark Trustworthiness Index.

### Highlights

- Seven-module audit pipeline with constructive evidence (the recovered
  equations themselves) and disposition labels (`target_leakage` vs
  `structural_constraint` vs `redundancy`).
- Planted-artifact self-validation: full recall, zero false positives
  (`synthaudit selftest`).
- `synthaudit` CLI with `--fail-below` for CI gating of data releases.
- Twelve cross-domain audit reports included (grades A through F), among
  them: the Grid Stability label is the sign of a shipped column; AI4I's
  failure rules and their nine generator-bug rows; Synthea's exact cost
  identities; 610 rows shared between NSL-KDD's official train and test
  files.
- Ablation, threshold/weight/seed stability tables, executed example
  notebooks, MkDocs documentation site, Docker setup, CI/CD workflows.

### Install

```bash
pip install "synthaudit[causal] @ git+https://github.com/rvndye/synthaudit.git@v0.1.0"
```

PyPI publication is planned; `dist/` artifacts are attached to this release.

Full changelog: https://github.com/rvndye/synthaudit/blob/main/CHANGELOG.md
