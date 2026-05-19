from __future__ import annotations

from pathlib import Path
from typing import Any

from redteaming.domain.models.attack import Attack
from redteaming.plugins.registry import FrameworkPlugin
from redteaming.plugins.garak.attack import GarakAttack


def build_attack(entry: dict[str, Any], index: int, path: Path) -> Attack:
    probe = entry.get("probe", "")
    if not probe:
        raise ValueError(f"{path}: attacks[{index}].probe is required for garak attacks")

    forbidden_keys = [k for k in ("input_field", "output_field", "req_template", "response_json_field") if k in entry]
    if forbidden_keys:
        raise ValueError(
            f"{path}: {', '.join(forbidden_keys)} must be configured in campaign.target, not in attack files"
        )

    config: dict[str, Any] = {"probe": probe}
    if "report_prefix" in entry:
        config["report_prefix"] = entry["report_prefix"]

    return GarakAttack(intent=entry["intent"], config=config)


GARAK_PLUGIN = FrameworkPlugin(name="garak", build_attack=build_attack)

__all__ = ["GARAK_PLUGIN", "GarakAttack", "build_attack"]


