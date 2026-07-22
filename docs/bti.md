# Benchmark Trustworthiness Index

## Pillars

Each pillar is a measured statistic in $[0,1]$, higher meaning more
trustworthy. With tolerance $s_0 = 0.9$ and excess
$e(s; s_0) = \max(0, (s-s_0)/(1-s_0))$:

| Pillar | Estimator |
|---|---|
| **L** label integrity | $1 - e(\hat{s}; s_0)$ where $\hat{s}$ is the best trivial-mechanism score for the target (identities and rules involving it, best single feature, skill-banded sweep) |
| **F** feature integrity | one minus the fraction of artifact columns (derived, components, leaky, duplicates, constants) |
| **H** difficulty headroom | one minus the saturation excess of an honest-view model over its baseline |
| **R** sampling realism | mean of duplicate, schedule-autocorrelation, lattice/uniform, and (when a test split is supplied) contamination subscores |
| **I** information density | effective linear rank of the stochastic core over its width |
| **T** transparency (optional) | fraction of four generator disclosures, only when metadata is supplied |

## Aggregation

$$\mathrm{BTI} = \prod_k \max(S_k, \epsilon)^{w_k / W}, \qquad
\epsilon = 0.01$$

with default weights L 0.30, F 0.20, H 0.20, R 0.15, I 0.15, T 0.15 and
grades A $\ge 0.80$, B $\ge 0.65$, C $\ge 0.50$, D $\ge 0.35$, else F.
The geometric mean is non-compensatory: exact label recovery caps the index
below the D threshold no matter the other pillars, and a release disclosing
nothing about its generator caps near C. The pillar vector, the recovered
evidence, and the honest-view definition are part of the score by contract;
the package will not render a scorecard without them.

## Grades are actions

A/B: usable with the recommended feature view and protocol warnings. C:
quarantine flagged columns, repair the task, re-audit. D/F: reported
performance on the shipped task chiefly measures generator recovery.

## Task relativity

The index scores a (dataset, target, task) triple. NSL-KDD grades near the
top for its attack label and would grade F for any task predicting a rate
feature inside a recovered identity. This mirrors how leakage itself is
defined relative to a prediction problem.

## Custom weights

Weights are overridable per audit (see the notebook
`notebooks/05_custom_bti.ipynb`). A stability study in the paper perturbs
each weight by half in both directions across twelve audits: one in ten
grades moves, always by a single band at a boundary, and no F verdict is
ever rescued.
