PY?=python
PIP?=pip

install:
	$(PIP) install -r requirements.txt

test:
	pytest -q

run:
	$(PY) -m bots.jit.main --env testnet
