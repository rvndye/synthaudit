"""Minimal SynthAudit example: audit a bundled dataset and export reports.

Run from the repository root:  python examples/quickstart.py
"""

import pandas as pd

from synthaudit import Audit

df = pd.read_csv("datasets/grid_stability.csv")

audit = Audit(
    df,
    target="stabf",
    name="grid_stability",
    metadata={
        "generator_described": True,
        "generator_code_available": False,
        "seed_reported": False,
        "artifacts_disclosed": True,
    },
)
results = audit.run()

print("BTI:", audit.bti, "grade:", results["scoring"]["grade"])
for finding in results["leakage"]["findings"][:5]:
    print(f"[{finding['severity']}] {finding['kind']}: {finding['detail'][:90]}")

audit.generate_report("grid_report.html")
print("wrote grid_report.html")
