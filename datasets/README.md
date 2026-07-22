# Bundled datasets

Three small public synthetic datasets ship with the repository so the
examples and notebooks run offline. Each keeps its original license.

| File | Source | Generation | License | Rows |
|---|---|---|---|---|
| `ai4i2020.csv` | UCI ML Repository #601 (Matzka, 2020) | synthetic milling process with documented failure rules | CC BY 4.0 | 10,000 |
| `grid_stability.csv` | UCI ML Repository #471 (Arzamasov et al., 2018) | Decentral Smart Grid Control simulation | CC BY 4.0 | 10,000 |
| `synthea_medications.csv.gz` | Synthea SyntheticMass 1k sample (Walonoski et al., 2018) | agent-based synthetic EHR generator | Apache-2.0 | 42,989 |

Attribution: AI4I 2020 Predictive Maintenance Dataset, S. Matzka, UCI
Machine Learning Repository. Electrical Grid Stability Simulated Data,
V. Arzamasov, UCI Machine Learning Repository. Synthea synthetic patient
records, The MITRE Corporation.

The remaining cohort datasets audited in `reports/` (NSL-KDD, UNSW-NB15,
BATADAL, Tennessee Eastman, further Synthea tables, IBM TabFormer) are not
redistributed here; fetch them with:

```bash
bash scripts/download_datasets.sh
```
