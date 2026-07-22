.PHONY: help install dev lint format test coverage selftest audit-example notebooks docs docs-serve build clean

help:            ## list available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

install:         ## install the package
	pip install .

dev:             ## editable install with all dev extras
	pip install -e ".[dev,causal,notebook]"

lint:            ## ruff lint + format check
	ruff check src tests scripts
	ruff format --check src tests scripts

format:          ## apply ruff formatting
	ruff format src tests scripts
	ruff check --fix src tests scripts

test:            ## run the test suite
	pytest -q

coverage:        ## tests with coverage report
	pytest -q --cov=synthaudit --cov-report=term-missing --cov-report=xml

selftest:        ## planted-artifact self-validation
	python -m synthaudit selftest

audit-example:   ## audit the bundled datasets into reports/
	python -m synthaudit audit datasets/grid_stability.csv --target stabf --name grid_stability --html reports/grid_stability_report.html
	python -m synthaudit audit datasets/ai4i2020.csv --target "Machine failure" --name ai4i2020 --html reports/ai4i2020_report.html

notebooks:       ## execute all example notebooks in place
	for nb in notebooks/*.ipynb; do jupyter nbconvert --to notebook --execute --inplace "$$nb"; done

docs:            ## build the documentation site strictly
	mkdocs build --strict

docs-serve:      ## serve docs locally with live reload
	mkdocs serve

build:           ## build sdist and wheel, then check metadata
	python -m build
	twine check dist/*

clean:           ## remove build artifacts and caches
	rm -rf build dist *.egg-info src/*.egg-info site .pytest_cache .ruff_cache .coverage coverage.xml htmlcov
