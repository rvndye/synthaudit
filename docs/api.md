# API reference

## `synthaudit.Audit`

```python
Audit(data, target=None, name="dataset", metadata=None, test_data=None,
      seed=42, modules=None, identity_kwargs=None)
```

| Parameter | Type | Meaning |
|---|---|---|
| `data` | DataFrame or CSV path | the released dataset to audit |
| `target` | str or None | benchmark target column; None runs a target-free audit |
| `name` | str | display name used in reports |
| `metadata` | dict or None | transparency disclosures: `generator_described`, `generator_code_available`, `seed_reported`, `artifacts_disclosed` (booleans); enables the T pillar |
| `test_data` | DataFrame or None | held-out split; activates the contamination check and its realism subscore |
| `seed` | int | controls all sampling and model fitting |
| `modules` | set or None | subset of `{"profile","identity","determinism","causal","leakage"}`; None runs all |
| `identity_kwargs` | dict or None | miner options: `max_rounds` (peeling cap, default 5), `mine_fds` (default True) |

### Methods

| Method | Returns |
|---|---|
| `run(verbose=True)` | the full results tree (dict) |
| `generate_report(path=None)` / `export_html(path)` | writes the self-contained HTML report |
| `export_pdf(path)` | one-page matplotlib scorecard |
| `export_json(path)` | machine-readable findings |
| `export_notebook(path)` | reproduction notebook |
| `bti` (property) | scalar index after `run()` |

### The results tree

| Key | Contents |
|---|---|
| `profile` | types, missingness, constants, duplicates, lattice and uniformity screens |
| `identity` | `identities` (each with `type`, `equation`, `r2`, `disposition`, `constraint_members`, `derived_member`), `functional_dependencies`, `rule_derived_labels`, `derived_columns` |
| `determinism` | per-column `sweep` rows with `score`, `skill`, `baseline`, `class` |
| `causal` | PC edges on the stochastic core, excluded columns, sortability estimates |
| `leakage` | `findings` with severities, `single_feature_screens`, `target_autocorrelation`, `train_test_overlap_rows` |
| `taxonomy` | `roles` per column and role `counts` |
| `scoring` | `pillars`, `weights`, `bti`, `grade`, `evidence`, `interpretation` |
| `recommendations` | drop and quarantine lists, `recommended_feature_view`, suggested targets and tasks, protocol warnings |
| `meta` | shape, target, runtime, package version |

## Validation testbed

```python
make_planted(n=20000, seed=42, extended=False) -> (DataFrame, truth)
score_detection(results, truth) -> dict     # recall, negative_control_pass
synthaudit.testbed.truth_roles(extended)    # acceptable role sets per column
synthaudit.testbed.role_accuracy(results, extended)
```

`extended=True` adds an eleventh artifact outside the identity miners'
function classes, catchable only by the determinism sweep; it exists so
ablations have a probe for that module.

## Command line

```text
synthaudit audit DATA.csv [--target COL] [--name NAME] [--test-data TEST.csv]
                          [--metadata KEY=VAL]... [--html P] [--pdf P]
                          [--json P] [--notebook P] [--seed N]
                          [--fail-below {A,B,C,D}] [--quiet]
synthaudit selftest [--extended] [--n N] [--seed N] [--quiet]
synthaudit version
```

`--fail-below` makes the process exit nonzero when the grade falls below the
bar, for CI gating. `selftest` exits nonzero unless recall and the
negative-control pass rate are both perfect.

## Thresholds

Every operating point is a named constant with a documented default
(exactness $1-10^{-9}$, near band $0.995$, rule fidelity $0.999$ with
imbalance guards, FD $g_3 \le 0.005$ with dependent non-degeneracy,
single-feature flag $0.95$, sweep bands $0.999/0.98/0.9$ on skill, schedule
flag $|\rho_1| > 0.5$, and the BTI's $s_0 = 0.9$, saturation $0.995$,
floor $0.01$). See `synthaudit/_util.py` and the module constants.
