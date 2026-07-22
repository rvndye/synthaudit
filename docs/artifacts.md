# Artifact taxonomy

Eight artifact classes recur across domains. A1 through A6 are
*constructive*: the audit outputs the generating relation itself, checkable
by anyone with the file.

| Class | Pattern | Real example | Benchmark effect |
|---|---|---|---|
| A1 linear identity | $y = \beta^\top x + c$ exactly | cost = power x tariff | rank-deficient design; members reconstruct each other |
| A2 balance constraint | $\sum_i a_i x_i + c = 0$ | Grid: $p_4 = -(p_1+p_2+p_3)$ | one column redundant by construction |
| A3 power law | $y = C\prod x_i^{a_i}$ | Synthea: TOTALCOST = BASE_COST x DISPENSES | invisible to linear screens; under-detected by tree probes |
| A4 regime-affine | $y = \beta^\top x + \gamma(c)$ | cooling eff = base(type) - 0.015 age | masked categories embedded in continuous columns |
| A5 rule-derived label | label = threshold rules(x) | AI4I machine failure | benchmark task is rule re-identification |
| A6 sign/threshold label | $y = 1\{x > t\}$ | Grid: stabf = sign(stab) | the answer key ships in the same file |
| A7 sampling artifact | uniform/lattice marginals, duplicates, constants | KDD'99 duplicate rows | splits leak; realism claims fail |
| A8 schedule leakage | target in contiguous blocks | BATADAL attack windows | random CV leaks event context |

## Dispositions

Recovered relations are classified relative to the audited target:

- `target_leakage`: the target sits in the relation's variable set. The
  posed task is answerable by arithmetic regardless of the relation's
  scientific legitimacy.
- `structural_constraint`: the relation lives among non-target columns.
  Physics and accounting are not leakage; they are charged to feature
  integrity as redundancy and recommended for de-duplication in feature
  views.
- `redundancy`: duplicated or near-copied columns.

## Column roles

Every column receives exactly one role: `target`, `input`,
`derived_deterministic`, `near_deterministic`, `label_component`,
`leaky_feature`, `duplicate`, `constant`, `identifier`, `datetime`, or
`no_signal`, with a documented precedence order. Role assignments drive the
honest feature view and the feature-integrity pillar.
