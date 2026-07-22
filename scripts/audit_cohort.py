"""Regenerate the twelve-audit cohort reports and summary table.

Run scripts/download_datasets.sh first (bundled datasets work without it,
missing datasets are skipped with a notice).
"""

import glob
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

from synthaudit import Audit

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "datasets")
OUT = os.path.join(HERE, "..", "reports")

NSL_COLS = [
    "duration",
    "protocol_type",
    "service",
    "flag",
    "src_bytes",
    "dst_bytes",
    "land",
    "wrong_fragment",
    "urgent",
    "hot",
    "num_failed_logins",
    "logged_in",
    "num_compromised",
    "root_shell",
    "su_attempted",
    "num_root",
    "num_file_creations",
    "num_shells",
    "num_access_files",
    "num_outbound_cmds",
    "is_host_login",
    "is_guest_login",
    "count",
    "srv_count",
    "serror_rate",
    "srv_serror_rate",
    "rerror_rate",
    "srv_rerror_rate",
    "same_srv_rate",
    "diff_srv_rate",
    "srv_diff_host_rate",
    "dst_host_count",
    "dst_host_srv_count",
    "dst_host_same_srv_rate",
    "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate",
    "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate",
    "dst_host_srv_serror_rate",
    "dst_host_rerror_rate",
    "dst_host_srv_rerror_rate",
    "class",
    "difficulty",
]

META_OPEN = {
    "generator_described": True,
    "generator_code_available": True,
    "seed_reported": False,
    "artifacts_disclosed": False,
}
META_DESC = {
    "generator_described": True,
    "generator_code_available": False,
    "seed_reported": False,
    "artifacts_disclosed": False,
}
META_DISC = {
    "generator_described": True,
    "generator_code_available": False,
    "seed_reported": False,
    "artifacts_disclosed": True,
}


def p(*parts):
    return os.path.join(DATA, *parts)


def load_tep():
    frames = []
    for f in sorted(glob.glob(p("tep", "d*_te.dat"))):
        fault = int(os.path.basename(f)[1:3])
        arr = np.loadtxt(f)
        cols = [f"xmeas_{i}" for i in range(1, 42)] + [f"xmv_{i}" for i in range(1, 12)]
        d = pd.DataFrame(arr, columns=cols)
        d["fault"] = fault
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def jobs():
    yield ("grid_stability", pd.read_csv(p("grid_stability.csv")), "stabf", META_DISC, None)
    yield ("ai4i2020", pd.read_csv(p("ai4i2020.csv")), "Machine failure", META_DISC, None)
    yield (
        "synthea_medications",
        pd.read_csv(p("synthea_medications.csv.gz")),
        "TOTALCOST",
        META_OPEN,
        None,
    )

    optional = [
        ("nsl_kdd", "KDDTrain+.txt"),
        ("batadal03", "BATADAL_dataset03.csv"),
        ("batadal04", "BATADAL_dataset04.csv"),
        ("unsw_nb15", "UNSW_train.csv"),
        ("tep_braatz", os.path.join("tep", "d00_te.dat")),
        ("synthea_encounters", os.path.join("synthea", "csv", "encounters.csv")),
        ("synthea_procedures", os.path.join("synthea", "csv", "procedures.csv")),
        ("synthea_patients", os.path.join("synthea", "csv", "patients.csv")),
    ]
    have = {name for name, path in optional if os.path.exists(p(path))}
    missing = [name for name, _ in optional if name not in have]
    if missing:
        print("skipping (run scripts/download_datasets.sh):", ", ".join(missing))

    if "nsl_kdd" in have:
        tr = pd.read_csv(p("KDDTrain+.txt"), header=None, names=NSL_COLS)
        te = pd.read_csv(p("KDDTest+.txt"), header=None, names=NSL_COLS)
        yield ("nsl_kdd", tr, "class", META_DESC, te)
    if "batadal03" in have:
        b = pd.read_csv(p("BATADAL_dataset03.csv"))
        b.columns = [c.strip() for c in b.columns]
        yield ("batadal03", b, None, META_DISC, None)
    if "batadal04" in have:
        b = pd.read_csv(p("BATADAL_dataset04.csv"))
        b.columns = [c.strip() for c in b.columns]
        yield ("batadal04", b, "ATT_FLAG", META_DISC, None)
    if "unsw_nb15" in have:
        yield (
            "unsw_nb15",
            pd.read_csv(p("UNSW_train.csv")),
            "attack_cat",
            META_DESC,
            pd.read_csv(p("UNSW_test.csv")),
        )
    if "tep_braatz" in have:
        yield ("tep_braatz", load_tep(), "fault", META_OPEN, None)
    for tbl, tgt in [
        ("encounters", "TOTAL_CLAIM_COST"),
        ("procedures", "BASE_COST"),
        ("patients", "HEALTHCARE_EXPENSES"),
    ]:
        if f"synthea_{tbl}" in have:
            d = pd.read_csv(p("synthea", "csv", f"{tbl}.csv"))
            yield (f"synthea_{tbl}", d, tgt, META_OPEN, None)


def main():
    rows = []
    for name, df, target, meta, test in jobs():
        print(f"=== {name} ===", flush=True)
        audit = Audit(df, target=target, name=name, metadata=meta, test_data=test)
        res = audit.run()
        audit.export_html(os.path.join(OUT, f"{name}_report.html"))
        audit.export_json(os.path.join(OUT, f"{name}_audit.json"))
        s = res["scoring"]
        rows.append(
            {
                "dataset": name,
                "target": target,
                "BTI": s["bti"],
                "grade": s["grade"],
                **{k: v for k, v in s["pillars"].items()},
            }
        )
        pd.DataFrame(rows).to_csv(os.path.join(OUT, "cohort_summary_regenerated.csv"), index=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
