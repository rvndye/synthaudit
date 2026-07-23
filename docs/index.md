# SynthAudit

**Audit synthetic datasets for generator artifacts before machine learning.**

Synthetic and simulated datasets circulate as ordinary ML benchmarks, yet many
quietly ship their own answer key: labels that are closed-form functions of
shipped columns, features that re-express one another algebraically, balance
constraints, and scheduling structure that random cross-validation exploits.
Models then solve the *generator* rather than the task.

SynthAudit is a reference-free auditor: it takes only the released file (no
real source data, no generator access), recovers the artifacts constructively
(the equations themselves, not just anomaly flags), classifies every column,
separates benchmark leakage from legitimate physical structure, and scores
the release with a decomposable Benchmark Trustworthiness Index.

```bash
pip install synthaudit
```

```python
from synthaudit import Audit

audit = Audit(df, target="stabf", name="grid")
results = audit.run()
audit.generate_report()
```

## Where to start

New users: [Installation](installation.md), then the
[Quick start](quickstart.md), then the [Tutorial](tutorial.md), which walks
a real audit end to end. For the ideas behind the tool, read
[Theory](theory.md) and the [artifact taxonomy](artifacts.md); for the
scoring, the [BTI page](bti.md). Contributors should head for the
[developer guide](developer-guide.md).

## Headline results

On a planted-artifact testbed the auditor achieves full recall with zero
false positives across seeds. Across twelve public synthetic releases in
seven domains it recovered the Grid Stability label's sign rule, AI4I's
documented failure rules together with their nine generator-bug rows,
Synthea's exact cost identities, and 610 rows shared between NSL-KDD's
official train and test files, while correctly clearing structurally honest
exports such as Tennessee Eastman and BATADAL. The methodology paper is
under submission; audit reports live in the repository's `reports/` folder.
