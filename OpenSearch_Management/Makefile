PY=python
VENV=.venv
BIN=$(VENV)/bin
ACT=source $(BIN)/activate

venv:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install -U pip

install: venv
	$(BIN)/pip install -e .[dev]

fmt:
	$(BIN)/ruff format .

lint:
	$(BIN)/ruff check .

typecheck:
	$(BIN)/mypy .

test:
	$(BIN)/pytest --maxfail=1 --disable-warnings --cov=opensearch_management --cov-report=term-missing

audit:
	$(BIN)/pip-audit

.PHONY: venv install fmt lint typecheck test audit
