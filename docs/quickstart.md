# Quick start

## Sixty seconds, Python API

```python
import pandas as pd
from synthaudit import Audit

df = pd.read_csv("datasets/grid_stability.csv")   # bundled with the repo

audit = Audit(
    df,
    target="stabf",
    name="grid_stability",
    metadata={                       # optional: drives the Transparency pillar
        "generator_described": True,
        "generator_code_available": False,
        "seed_reported": False,
        "artifacts_disclosed": True,
    },
)
results = audit.run()

print(audit.bti, results["scoring"]["grade"])     # 0.256 F
audit.generate_report("grid_report.html")
```

The console log narrates each module; the HTML report contains the scorecard,
every recovered relation with its disposition, the findings list, the column
taxonomy, and the recommendations.

## Sixty seconds, command line

```bash
synthaudit audit datasets/grid_stability.csv --target stabf \
    --html grid_report.html --json grid_audit.json
```

## Auditing as a CI gate

```bash
synthaudit audit train.csv --target label --fail-below C
```

The process exits nonzero when the grade falls below the bar, so a data
pipeline can refuse to train on a release that ships its own answer key.

## What you should see on Grid Stability

Three critical findings: the target is recoverable via the threshold rule
`stabf == 'unstable' iff stab > 0`; `stab` is therefore a label component;
and single-feature dominance confirms it. One structural constraint: the
power balance `p4 = -(p1+p2+p3)`, correctly *not* treated as leakage. Grade
F, with the honest task (drop `stab` and `p4`) still meaningful at about
94 percent accuracy against a 65 percent base rate.
