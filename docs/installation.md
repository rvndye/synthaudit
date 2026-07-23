# Installation

SynthAudit requires Python 3.11 or newer and is tested on 3.11 and 3.12 across Linux, macOS, and Windows.

## From PyPI (recommended)

SynthAudit is published on [PyPI](https://pypi.org/project/synthaudit/):

```bash
pip install synthaudit
```

The causal structure scan needs one optional dependency:

```bash
pip install "synthaudit[causal]"
```

## Developer installation (from source)

```bash
git clone https://github.com/rvndye/synthaudit.git
cd synthaudit
pip install -e ".[dev,causal,notebook]"
pytest -q         # 15 tests, ~30 s
```

## Docker

```bash
docker compose run selftest          # planted-artifact validation
docker compose up notebooks          # JupyterLab with the examples on :8888
```

## Verifying the installation

```bash
synthaudit selftest
```

This generates the planted-artifact testbed and checks that all eleven
artifacts are detected and all negative controls stay clean. If it prints
`"recall": 1.0` and `"negative_control_pass": 1.0`, your installation is
sound.
