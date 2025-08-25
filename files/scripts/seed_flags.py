"""
Seeds local feature flags into .local_flags.json (dev only).
"""
import json, os, pathlib

FLAGS_PATH = ".local_flags.json"
DEFAULT_FLAGS = {
    "feature:MM-002:enabled": True,
    "feature:ENCH-CP-001:enabled": True,
    "feature:ENCH-HEDGE-005:enabled": False,
    "feature:OBI-002:enabled": True
}

def main():
    if os.path.exists(FLAGS_PATH):
        print(f"{FLAGS_PATH} already exists; not overwriting.")
        return
    with open(FLAGS_PATH, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_FLAGS, f, indent=2)
    print(f"Wrote {FLAGS_PATH} with default flags.")

if __name__ == "__main__":
    main()
