.PHONY: install dev test test-unit test-e2e test-jit test-hedge test-trend test-cov test-ci clean-test lint

PY?=python3

install:
	$(PY) -m pip install -U pip
	$(PY) -m pip install -r requirements.txt

dev:
	$(PY) -m pip install -r requirements-dev.txt
	pre-commit install || true

# Main test targets
test:
	$(PY) -m pytest

test-unit:
	$(PY) -m pytest -m "unit"

test-integration:
	$(PY) -m pytest -m "integration"

test-e2e:
	$(PY) -m pytest -m "e2e"

test-regression:
	$(PY) -m pytest -m "regression"

test-performance:
	$(PY) -m pytest -m "perf"

# Bot-specific tests
test-jit:
	$(PY) -m pytest tests/test_jit_bot.py

test-hedge:
	$(PY) -m pytest tests/test_hedge_bot.py

test-trend:
	$(PY) -m pytest tests/test_trend_bot.py

# Test by speed/type
test-fast:
	$(PY) -m pytest -m "not (slow or e2e or perf)"

test-slow:
	$(PY) -m pytest -m "slow"

test-network:
	$(PY) -m pytest -m "network"

# Coverage testing
test-cov:
	$(PY) -m pytest --cov-report=html

test-cov-xml:
	$(PY) -m pytest --cov-report=xml

# CI/CD test suite
test-ci:
	$(PY) -m pytest --junitxml=test-results.xml

# Development workflow
test-dev:
	$(PY) -m pytest -m "unit or integration" --maxfail=5

# Clean test artifacts
clean-test:
	rm -rf .coverage htmlcov test-results.xml .pytest_cache
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete

# Lint and format check
lint:
	ruff check bots/ libs/ tests/
	mypy bots/ libs/ tests/ || true

# Full development workflow
dev-setup: dev lint test-unit

# Run all tests with coverage
test-all: test-unit test-e2e test-cov

run:
	$(PY) -m bots.jit.main --env testnet

tag:
	bash scripts/tag_release.sh v1.17.0-rc2
