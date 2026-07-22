# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-22

First public release, accompanying the SynthAudit methodology paper
(under submission).

### Added
- Seven-module audit pipeline: profiling, identity mining (minimal Gram-based
  OLS with iterative peeling, power laws, regime-affine equations, functional
  dependencies with non-degeneracy guard, rule and threshold extraction),
  out-of-sample determinism sweep (skill-banded), advisory causal scan with
  sortability diagnostics, leakage audit (derived targets, label components,
  target descendants, single-feature dominance, schedule leakage, train/test
  contamination), variable taxonomy, and recommendations.
- Benchmark Trustworthiness Index: five measured pillars plus optional
  transparency pillar, weighted geometric mean aggregation with proved
  non-compensation, invariance, decomposition, and leakage-sensitivity
  properties; disposition labels separating target leakage from structural
  constraints.
- Planted-artifact validation testbed (`make_planted`, `score_detection`)
  with extended mode and role-accuracy scoring.
- Exports: self-contained HTML report, one-page PDF scorecard, JSON findings,
  reproduction notebook.
- `synthaudit` command-line interface with `audit`, `selftest`, and `version`
  subcommands, including `--fail-below` for CI gating.
- Twelve cross-domain audit reports, ablation and stability tables, and
  publication figures as repository assets.
- Documentation site (MkDocs Material), six executed example notebooks,
  Docker and docker-compose setups, CI/CD workflows, and community files.

[0.1.0]: https://github.com/rvndye/synthaudit/releases/tag/v0.1.0
