# Audit reports

Self-contained HTML audit reports for the twelve-release cohort in the
paper, plus `cohort_summary.csv` with every pillar, grade, and finding
count. Regenerate everything with:

```bash
bash scripts/download_datasets.sh
python scripts/audit_cohort.py
```

Reports for the three bundled datasets can be regenerated offline with
`make audit-example`.
