from dataclasses import dataclass

@dataclass
class AttributionArm:
    name: str  # "with_obi" or "default"

def select_arm(cfg: dict) -> AttributionArm:
    if cfg.get("obi_ab", {}).get("enabled", False):
        return AttributionArm("with_obi")
    return AttributionArm("default")
