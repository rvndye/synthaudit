"""SynthAudit — audit synthetic datasets for generator artifacts before ML.

Usage
-----
>>> from synthaudit import Audit
>>> audit = Audit(df, target="machine_failure", name="ai4i2020")
>>> results = audit.run()
>>> audit.generate_report()          # self-contained HTML
>>> audit.export_pdf("report.pdf")   # scorecard PDF
>>> audit.export_json("audit.json")  # machine-readable findings
"""

__version__ = "0.1.0"

from .audit import Audit
from .testbed import make_planted, score_detection

__all__ = ["Audit", "make_planted", "score_detection", "__version__"]
