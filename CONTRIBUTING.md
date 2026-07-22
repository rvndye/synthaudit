# Contributing to SynthAudit

Thank you for considering a contribution. This project aims to make
pre-training audits of synthetic datasets a community standard, and it grows
through exactly three kinds of work: better detectors, more audited datasets,
and clearer documentation.

## Development setup

```bash
git clone https://github.com/rvndye/synthaudit.git
cd synthaudit
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,causal,notebook]"
pytest -q            # full suite, ~30 s
make lint            # ruff check + format check
```

`make help` lists every task. The planted-artifact self-test
(`synthaudit selftest`) must pass at full recall with zero false positives
before and after your change; it is the project's conscience.

## What makes a good contribution

**New detectors.** Add the miner in a focused module under `src/synthaudit/`,
register its findings with a `disposition`, extend the planted testbed with
an artifact only your detector can catch, and add the negative control that
proves it does not over-fire. A detector without a testbed artifact and an
imbalance/degeneracy guard will not be merged; the project has been bitten
before, and the story is in the paper's limitations.

**New dataset audits.** Add a loader stanza to `scripts/audit_cohort.py`, a
row to `datasets/README.md` with license and provenance, and open a PR with
the generated report. Only publicly redistributable or downloadable datasets.

**Docs and examples.** Notebooks must execute top to bottom
(`make notebooks`), and documentation must build strictly (`make docs`).

## Style and quality bar

Ruff enforces formatting and linting (`pyproject.toml` carries the config).
Type hints are welcome but not yet enforced. Every public function needs a
docstring; every threshold needs a name, a default in `_util.py` or module
constants, and a row in the documentation's thresholds table. Keep runtime
frugal: audits should stay in seconds-to-minutes on one core.

## Pull requests

Branch from `main`, keep PRs focused, fill in the template, and make sure CI
is green. Squash-merge is the default. By contributing you agree that your
contributions are licensed under Apache-2.0.

## Questions

Open a GitHub Discussion for design questions, an issue for bugs, and use the
*Audit finding* issue template to report generator artifacts you discovered
in public benchmarks with SynthAudit.
