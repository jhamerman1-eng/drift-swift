# v0.9 Scaffold (Relink Package)

This is a drop-in v0.9 update intended to be applied at the root of your repo.

## TL;DR
```bash
bash apply_patch.sh
# optionally set a remote & push
bash relink_v0_9.sh https://github.com/your-org/your-repo.git
```

## Run (Dev)
```bash
# 1) create & fill .env from .env.example
cp .env.example .env

# 2) install deps
pip install -r requirements.txt
# or
pip install -e .

# 3) seed flags (local json file)
python scripts/seed_flags.py

# 4) launch JIT bot (testnet)
python -m bots.jit.main --env testnet
# metrics at :9108/metrics
```

## Test
```bash
pytest -q
```
