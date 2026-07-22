# Architecture

One `Audit.run()` call executes seven modules in sequence; each consumes the
outputs of its predecessors.

```
released CSV
   -> M1 Profiling          types, constants, duplicates, lattice/uniform screens
   -> M2 Identity mining    minimal OLS + peeling, power laws, regimes, FDs, rules, thresholds
   -> M3 Determinism sweep  out-of-sample predictability from the stochastic core
   -> M4 Causal scan        de-determinized PC + sortability diagnostics (advisory)
   -> M5 Leakage audit      derived targets, components, descendants, schedule, contamination
   -> Taxonomy              one role per column
   -> M6 BTI                pillar vector + geometric-mean scalar + grade
   -> M7 Recommendations    drop/quarantine lists, honest view, protocol warnings
   -> Reports               HTML / PDF / JSON / notebook
```

## Design decisions worth knowing

**Gram-matrix mining.** The numeric block's Gram matrix is computed once;
any subset OLS then costs cubic time in the support size, independent of the
row count, which makes greedy backward elimination (for *minimal* supports)
affordable on every column.

**Iterative peeling.** Exact constraints are symmetric and chain through
duplicates, so single-pass mining mis-attributes roles. SynthAudit groups
exact findings by variable set, elects one derived member per constraint
(latest column in file order, never the audit target), removes it, and
re-mines to a fixed point. The label-integrity pillar is provably invariant
to the election heuristic.

**De-determinization before causal discovery.** Deterministic relations
violate faithfulness and corrupt conditional-independence tests, so derived
columns are removed before the PC scan, and varsortability-style diagnostics
are reported as generator fingerprints rather than trusted structure.

**Skill-adjusted screens everywhere.** See the theory page's section on the
auditor's own adversary.

## Module boundaries in code

| Module | File |
|---|---|
| Profiling | `synthaudit/profiling.py` |
| Identity mining | `synthaudit/identity.py` |
| Determinism sweep | `synthaudit/determinism.py` |
| Causal scan | `synthaudit/causal.py` |
| Leakage audit | `synthaudit/leakage.py` |
| Taxonomy | `synthaudit/taxonomy.py` |
| Scoring (BTI) | `synthaudit/scoring.py` |
| Recommendations | `synthaudit/recommend.py` |
| Reports | `synthaudit/report.py` |
| Orchestrator | `synthaudit/audit.py` |
| Validation testbed | `synthaudit/testbed.py` |
| CLI | `synthaudit/cli.py` |

An ablation study in the paper shows what each module carries: without
identity mining, recall collapses and broken benchmarks pass; without the
determinism sweep, out-of-class nonlinear derivations slip through; without
peeling, negative controls fail.
