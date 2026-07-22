"""Packaging hygiene tests."""

import pathlib
import tomllib

import synthaudit


def test_version_single_source():
    root = pathlib.Path(__file__).resolve().parents[1]
    meta = tomllib.loads((root / "pyproject.toml").read_text())
    assert meta["project"]["version"] == synthaudit.__version__


def test_public_api_surface():
    assert set(synthaudit.__all__) >= {"Audit", "make_planted", "score_detection"}
