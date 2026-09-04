# Every target runs tools through `$(PYTHON) -m`, never a bare `ruff`/`mypy`/
# `pytest` from PATH. A tool resolved from PATH can come from a different
# environment than the package under test — a globally installed, isolated mypy
# cannot see pytest or hypothesis, and silently type-checks the test suite
# against missing imports. Going through the interpreter guarantees the tools
# and the package are the same environment.
#
# PYTHON defaults to whatever `python` is active, so activating the project
# virtualenv is the whole setup. Override it to target another interpreter:
#   make check PYTHON=.venv/bin/python

PYTHON ?= python

.PHONY: check lint types test guards install-dev

check: lint types test

lint:
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m ruff format --check src tests

types:
	$(PYTHON) -m mypy --strict src tests

test:
	$(PYTHON) -m pytest -q

# The Phase 0 exit-criteria guards on their own, for CI to report separately.
guards:
	$(PYTHON) -m pytest -q tests/unit/test_project_guards.py \
		tests/integration/test_reproducibility.py

install-dev:
	$(PYTHON) -m pip install -e ".[dev]"
