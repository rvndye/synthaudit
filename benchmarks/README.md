# Benchmark and validation assets

This folder is the quantitative backbone of the paper's claims and doubles
as a benchmark for *other* auditing tools.

| File | Contents |
|---|---|
| `ablation.csv` | leave-one-module-out ablation on the extended planted testbed plus flagship findings on three real pilots |
| `sensitivity_s0.csv` | BTI grades across the label-integrity tolerance sweep |
| `sensitivity_near.csv` | identity counts across the near-identity threshold sweep |
| `seed_stability.csv` | honest and naive scores across seeds on three flagship audits |
| `stability.json` | aggregate stability statistics (threshold and weight perturbations) |

## The planted-artifact protocol

`synthaudit.make_planted(n, seed, extended=True)` generates a table with
eleven known artifacts spanning every detector class plus negative
controls, and `score_detection` computes planted recall and the
negative-control pass rate. We propose this pair of numbers as the minimum
reporting standard for any synthetic-dataset auditor, and we welcome
comparisons: open an issue with the *Audit finding* template.
