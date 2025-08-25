import yaml
from pathlib import Path

FLAGS = {
    "feature_flags": {
        "obi_enabled": False,
        "trend_enabled": True,
        "hedge_enabled": True,
    }
}

OUT = Path("configs/risk/risk_modes.yaml")

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        data = yaml.safe_load(OUT.read_text()) or {}
    else:
        data = {}
    data.update(FLAGS)
    OUT.write_text(yaml.safe_dump(data, sort_keys=False))
    print(f"Seeded flags → {OUT}")