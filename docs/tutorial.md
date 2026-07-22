# Tutorial: anatomy of an audit

This walkthrough audits the bundled AI4I 2020 predictive-maintenance dataset
and reads every part of the result. Run it in the
`notebooks/03_auditing_ai4i.ipynb` notebook or paste along.

## 1. Run the audit

```python
import pandas as pd
from synthaudit import Audit

df = pd.read_csv("datasets/ai4i2020.csv")
audit = Audit(df, target="Machine failure", name="ai4i2020")
results = audit.run()
```

## 2. Read the verdict first

```python
results["scoring"]
```

Grade F with the label-integrity pillar near zero. The evidence list names
the mechanism: `Machine failure = decision_rules(HDF, PWF, OSF, TWF, ...)`
at fidelity 0.9991.

## 3. Inspect the recovered mechanism

```python
rule = results["identity"]["rule_derived_labels"][0]
print(rule["equation"], rule["fidelity"], rule["violating_rows_in_sample"])
print(rule["rules"][:400])
```

Nine rows violate the recovered rule. Those nine rows are the dataset's
independently documented generator bugs: rows where the shipped label
contradicts the shipped failure-mode flags. The audit's residuals localize
generator defects, which is the advantage of constructive evidence over
anomaly flags.

## 4. Read the taxonomy and the honest view

```python
results["taxonomy"]["counts"]
results["recommendations"]["drop_columns"]
results["recommendations"]["recommended_feature_view"]
```

The five failure-mode flags are `label_component`; the recommendations name
the honest feature view (raw process telemetry only) and the protocol
warnings. On that view a strong model scores about 0.978 against a 0.969
base rate: the famous 99.9 percent accuracies on this dataset are rule
recovery, not learning.

## 5. Exports

```python
audit.generate_report("ai4i_report.html")
audit.export_pdf("ai4i_scorecard.pdf")
audit.export_json("ai4i_audit.json")
audit.export_notebook("ai4i_repro.ipynb")
```

## 6. When the target is somewhere else

The index is a property of the (dataset, target) pair. Audit the same file
with a different target and the verdict changes accordingly; see the BTI
page's task-relativity discussion.
