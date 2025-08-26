.PHONY: install dev test run tag

PY?=python3

install:
	$(PY) -m pip install -U pip
	$(PY) -m pip install -r requirements.txt

dev:
	$(PY) -m pip install -r requirements.txt
	pre-commit install || true

test:
	$(PY) -m pytest -q || true

run:
	$(PY) -m bots.jit.main --env testnet

tag:
	bash scripts/tag_release.sh v1.17.0-rc2
