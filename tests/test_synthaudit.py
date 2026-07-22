"""SynthAudit test suite."""

import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import pytest

from synthaudit import Audit, make_planted, score_detection
from synthaudit.identity import (
    mine_functional_dependencies,
    mine_linear,
    mine_threshold_derivations,
)
from synthaudit.profiling import profile
from synthaudit.scoring import GRADES


@pytest.fixture(scope="module")
def planted():
    df, truth = make_planted(n=6000, seed=42)
    audit = Audit(df, target="target_y", name="test-planted")
    results = audit.run(verbose=False)
    return audit, results, truth


def test_linear_identity_recovery():
    rng = np.random.default_rng(0)
    a, b = rng.normal(0, 1, 2000), rng.normal(0, 1, 2000)
    df = pd.DataFrame({"a": a, "b": b, "y": 2 * a + 3 * b - 1, "z": rng.normal(0, 1, 2000)})
    found = mine_linear(df, ["a", "b", "y", "z"])
    eqs = [f for f in found if f["exact"]]
    assert any(set(f["predictors"]) <= {"a", "b", "y"} for f in eqs)


def test_power_law_recovery():
    rng = np.random.default_rng(0)
    x = rng.uniform(0.5, 3, 2000)
    w = rng.uniform(1, 2, 2000)
    df = pd.DataFrame({"x": x, "w": w, "p": 4.0 * x**2 / w, "n": rng.normal(0, 1, 2000)})
    found = mine_linear(df, list(df.columns))
    assert any(f["type"] == "power_law" and f["exact"] for f in found)


def test_threshold_derivation():
    rng = np.random.default_rng(0)
    s = rng.normal(0, 1, 3000)
    df = pd.DataFrame({"s": s, "lab": np.where(s > 0.3, "hi", "lo"), "o": rng.normal(0, 1, 3000)})
    found = mine_threshold_derivations(df, ["s", "o"])
    assert len(found) == 1
    assert found[0]["predictors"] == ["s"]
    assert abs(found[0]["threshold"] - 0.3) < 0.05


def test_functional_dependency():
    rng = np.random.default_rng(0)
    code = rng.integers(0, 20, 5000)
    df = pd.DataFrame(
        {"code": code, "desc": [f"item-{c}" for c in code], "val": rng.normal(0, 1, 5000)}
    )
    fds = mine_functional_dependencies(df, ["code", "desc"], [])
    assert any(f["determinant"] == "code" and f["dependent"] == "desc" and f["exact"] for f in fds)


def test_planted_full_recall(planted):
    _, results, truth = planted
    sc = score_detection(results, truth)
    assert sc["recall"] == 1.0, f"missed artifacts: {sc['rows']}"
    assert sc["negative_control_pass"] == 1.0


def test_bti_structure(planted):
    _, results, _ = planted
    s = results["scoring"]
    for k, v in s["pillars"].items():
        if v is not None:
            assert 0.0 <= v <= 1.0, f"pillar {k} out of range: {v}"
    assert 0.0 <= s["bti"] <= 1.0
    assert s["grade"] in {g for _, g in GRADES}
    # a dataset shipping a copy of its target must not grade above C
    assert s["grade"] in {"C", "D", "F"}


def test_taxonomy_partition(planted):
    _, results, _ = planted
    roles = results["taxonomy"]["roles"]
    df_cols = set(results["profile"]["columns"])
    assert set(roles) == df_cols  # every column classified exactly once


def test_exports(planted, tmp_path):
    audit, _, _ = planted
    h = audit.export_html(str(tmp_path / "r.html"))
    j = audit.export_json(str(tmp_path / "r.json"))
    p = audit.export_pdf(str(tmp_path / "r.pdf"))
    n = audit.export_notebook(str(tmp_path / "r.ipynb"))
    for f in (h, j, p, n):
        assert (tmp_path / f.split("/")[-1]).stat().st_size > 500


def test_profile_constants_and_duplicates():
    df = pd.DataFrame({"a": [1.0] * 100, "b": range(100)})
    df = pd.concat([df, df.iloc[:10]], ignore_index=True)
    prof = profile(df)
    assert "a" in prof["constant_cols"]
    assert prof["duplicate_rows"] == 10


def test_no_target_mode():
    df, _ = make_planted(n=2000, seed=1)
    audit = Audit(df, target=None, name="no-target")
    res = audit.run(verbose=False)
    assert res["scoring"]["pillars"]["L"] is None
    assert res["scoring"]["bti"] > 0
