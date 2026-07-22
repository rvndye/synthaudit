"""CLI tests."""

import json
import subprocess
import sys

import pytest

from synthaudit.cli import main
from synthaudit.testbed import make_planted


@pytest.fixture(scope="module")
def small_csv(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    df, _ = make_planted(n=3000, seed=1)
    path = d / "planted.csv"
    df.to_csv(path, index=False)
    return str(path)


def test_audit_command_exports(small_csv, tmp_path, capsys):
    html = tmp_path / "r.html"
    js = tmp_path / "r.json"
    rc = main(
        [
            "audit",
            small_csv,
            "--target",
            "target_y",
            "--name",
            "cli-test",
            "--html",
            str(html),
            "--json",
            str(js),
            "--quiet",
        ]
    )
    assert rc == 0
    assert html.stat().st_size > 1000
    payload = json.loads(js.read_text())
    assert payload["scoring"]["grade"] in "ABCDF"
    summary = json.loads(capsys.readouterr().out)
    assert summary["dataset"] == "cli-test"


def test_fail_below_gate(small_csv):
    # the planted set ships a copy of its target: must fail a B gate
    rc = main(
        [
            "audit",
            small_csv,
            "--target",
            "target_y",
            "--quiet",
            "--fail-below",
            "B",
        ]
    )
    assert rc == 1


def test_metadata_parsing_and_version(capsys):
    rc = main(["version"])
    out = capsys.readouterr().out.strip()
    assert rc == 0 and out.count(".") == 2


def test_console_entrypoint_runs():
    proc = subprocess.run(
        [sys.executable, "-m", "synthaudit", "version"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0 and proc.stdout.strip()


def test_selftest_small(capsys):
    rc = main(["selftest", "--n", "6000", "--quiet"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["recall"] == 1.0 and out["negative_control_pass"] == 1.0
