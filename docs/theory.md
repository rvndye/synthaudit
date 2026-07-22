# Theory

## Generators are structural causal models

Whatever produced a synthetic table (a physics simulator, agent rules, a
neural sampler) acted as a program of assignments
$X_j = f_j(\mathrm{pa}(X_j), \varepsilon_j)$ over an acyclic graph. Three
properties of synthetic data generating programs make auditing tractable:
mechanisms are frequently **degenerate** (many columns are exact functions of
others), mechanisms are **simple** (linear combinations, products, thresholds,
lookup tables, per-regime constants), and sampling designs are **visible**
(uniform draws, lattices, scripted schedules leave signatures). SynthAudit is
an estimator of exactly this structure.

## Benchmark validity and the artifact share

A benchmark is *trivialized* to the extent its achievable score is explained
by recoverable generator mechanisms rather than the relationship the task
nominally tests. With a strong learner scoring $s^{naive}$ on all shipped
columns and $s^{honest}$ on the post-audit feature view, over baseline $b$:

$$\rho = 1 - \frac{\max(s^{honest}-b,\,0)}{\max(s^{naive}-b,\,\epsilon)}$$

On AI4I 2020, $\rho = 0.71$: seventy-one percent of the measurable skill is
generator recovery. On Synthea medications, $\rho = 0.81$.

## Legitimate determinism versus leakage

Scientific legitimacy is a property of the generator; leakage is a property
of a *task*. A correct accounting identity is impeccable bookkeeping and
still fatal for the task of predicting its output. Every recovered relation
therefore carries a disposition: `target_leakage` when the target belongs to
the relation's variable set, `structural_constraint` when the relation lives
among non-target columns (charged to feature integrity as redundancy, never
called leakage), or `redundancy` for duplicated columns.

## Guarantees

The accompanying paper proves: range and strict monotonicity of the index;
a non-compensation cap (a floored pillar bounds the index by
$\epsilon^{w_k/W}$ regardless of all other pillars, so exact label recovery
forces grade F at default weights); weight-scale invariance and coherent
pillar removal; exact log-decomposition of the score into pillar
attributions; a leakage-sensitivity bound showing a shipped noisy copy of
the target with noise variance $\sigma^2$ forces
$L \le \frac{1}{1-s_0}\cdot\frac{\sigma^2}{v+\sigma^2}$, which prices
adversarial evasion; and termination, hitting, and election-invariance
properties of the iterative peeling procedure.

## The auditor's own adversary

Class imbalance can make screens hallucinate: a mostly-missing feature whose
non-missing rows are single-class yields vacuous perfect fits, and raw
accuracy on a 99.9 percent constant column looks deterministic. Every
classification score in SynthAudit is therefore *skill over the majority
baseline*, missing values are a category of their own, degenerate slices
return no evidence, and rule/FD miners carry explicit non-degeneracy guards.
This lesson was learned the honest way and is disclosed in the paper.
