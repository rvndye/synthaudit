# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | yes |

## Reporting a vulnerability

Please report suspected vulnerabilities privately via GitHub's
[security advisories](https://github.com/rvndye/synthaudit/security/advisories/new)
for this repository, or by email to erwinrandy3@gmail.com with the subject
line `SYNTHAUDIT SECURITY`. Please do not open public issues for security
reports. You can expect an acknowledgment within a week.

## Scope notes

SynthAudit reads untrusted CSV files with pandas and renders HTML reports
from dataset-derived strings. Findings of interest include: HTML injection
into generated reports from crafted column names or values, path traversal
in export paths, and denial-of-service via pathological inputs to the miners.
The HTML report escapes dataset-derived content; crafted inputs that escape
that escaping are in scope and appreciated.
