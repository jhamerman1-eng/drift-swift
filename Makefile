.PHONY: venv install run test lint fmt typecheck check ci

PY?=python3
PIP?=pip
VENV?=.venv
ACTIVATE=$(VENV)/bin/activate

venv:
	$(PY) -m venv $(VENV)
	. $(ACTIVATE); $(PIP) install --upgrade pip

install: venv
	. $(ACTIVATE); $(PIP) install -r requirements.txt

run:
	. $(ACTIVATE); python -m orchestrator.run

test:
	. $(ACTIVATE); pytest -q

lint:
	. $(ACTIVATE); ruff check .

fmt:
	. $(ACTIVATE); ruff format .

typecheck:
	. $(ACTIVATE); mypy --strict libs/ orchestrator/

check: lint typecheck test

ci: install check
