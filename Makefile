.PHONY: check lint types test install-dev

check: lint types test

lint:
	ruff check src tests
	ruff format --check src tests

types:
	mypy --strict src tests

test:
	pytest -q

install-dev:
	python -m pip install -e ".[dev]"
