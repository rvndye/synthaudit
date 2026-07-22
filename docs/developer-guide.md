# Developer guide

## Setup

```bash
git clone https://github.com/rvndye/synthaudit.git && cd synthaudit
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,causal,notebook]"
make lint test
```

## Project layout

`src/synthaudit/` holds one module per audit stage (see the architecture
page for the map); `tests/` mirrors it; `docs/` is this site; `notebooks/`
are executed examples; `scripts/` regenerate the cohort reports and
benchmark tables; `reports/`, `benchmarks/`, and `figures/` are committed
research assets.

## Adding a detector

1. Implement the miner in the right module (or a new one) and emit findings
   as dicts carrying at minimum `type`, `target`, `predictors`, a fit
   statistic, an `equation` string, and let `identity.run` assign the
   `disposition`.
2. Guard it. Every screen must state what happens under extreme class
   imbalance, missing data, and degenerate slices. Baseline-relative scores
   only; raw accuracy is banned by convention.
3. Plant it. Add an artifact to `testbed.make_planted` that only your
   detector catches, plus a negative control that proves it does not
   over-fire, and wire both into `score_detection`.
4. Test it: a unit test for the miner, plus the full-recall and
   negative-control assertions already in `tests/test_synthaudit.py`.
5. Document it: a row in the artifact taxonomy, a threshold entry, a line in
   the CHANGELOG.

## Release process

1. Bump `version` in `pyproject.toml` and `__version__` in
   `src/synthaudit/__init__.py` (a test enforces they match).
2. Update `CHANGELOG.md`.
3. `make lint test build docs` must all pass.
4. Tag `vX.Y.Z`, push, and create the GitHub release; attach `dist/*`.
5. `twine upload dist/*` for PyPI (maintainers only).
6. Zenodo archiving: link the repository once at zenodo.org (Log in with
   GitHub, flip the toggle for `rvndye/synthaudit` under GitHub settings),
   then every GitHub release is archived automatically with its own DOI.
   After the first archived release, add the concept DOI badge to the
   README (a commented template is already there) and the `doi` field to
   `CITATION.cff`.

## Style

Ruff handles linting and formatting (`make format`). Line length 100.
Docstrings on public functions. Thresholds are named constants, never inline
literals. Keep audits frugal: one core, seconds to minutes.
