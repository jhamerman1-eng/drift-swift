.PHONY: install run-jit run-hedge run-trend run-all fmt lint seed compose-up compose-down

install:
	poetry install --no-root

seed:
	poetry run python scripts/seed_flags.py

run-jit:
	poetry run python -m bots.jit.main --env $${DRIFT_ENV:-testnet} --metrics-port 9101

run-hedge:
	poetry run python -m bots.hedge.main --env $${DRIFT_ENV:-testnet} --metrics-port 9102

run-trend:
	poetry run python -m bots.trend.main --env $${DRIFT_ENV:-testnet} --metrics-port 9103

run-all:
	poetry run python -m orchestrator.main --env $${DRIFT_ENV:-testnet}

fmt:
	poetry run ruff check . --fix

lint:
	poetry run ruff check . && poetry run mypy .

compose-up:
	docker compose up -d

compose-down:
	docker compose down -v
