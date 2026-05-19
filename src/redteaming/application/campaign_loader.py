"""Parse a YAML campaign file and return a ready-to-run CampaignConfig."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from redteaming.application.campaign_config import CampaignConfig
from redteaming.domain.models.attack import Attack
from redteaming.plugins.registry import get_plugin, list_framework_names

logger = logging.getLogger(__name__)

_REQUIRED_TOP_KEYS = {"target", "attacks"}
_VALID_TOP_KEYS = {"campaign", "target", "attacks"}

def load_campaign(yaml_path: str | Path) -> CampaignConfig:
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Campaign file not found: {path}")

    raw = _read_yaml(path)
    _validate_top_level(raw, path)
    target_cfg = _parse_target(raw["target"], path)
    attacks = _load_attacks(raw.get("attacks"), path)

    campaign_meta = raw.get("campaign", {})
    logger.info(
        "Loaded campaign '%s' — %d attack(s) targeting '%s'",
        campaign_meta.get("name", path.stem),
        len(attacks),
        target_cfg["name"],
    )
    return CampaignConfig(
        campaign_name=campaign_meta.get("name", path.stem),
        target_name=target_cfg["name"],
        target_chat_url=target_cfg["chat_url"],
        target_reset_memory_url=target_cfg["reset_memory_url"],
        target_model=target_cfg["model"],
        target_architecture_type=target_cfg["architecture_type"],
        target_input_field=target_cfg["input_field"],
        target_output_field=target_cfg["output_field"],
        active_attacks=attacks,
    )


def load_attack(yaml_path: str | Path) -> Attack:
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Attack file not found: {path}")
    return _build_attack(_read_yaml(path), 0, path)


def _read_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at top level, got {type(data).__name__}")
    return data


def _validate_top_level(raw: dict, path: Path) -> None:
    missing = _REQUIRED_TOP_KEYS - raw.keys()
    if missing:
        raise ValueError(f"{path}: missing required top-level key(s): {', '.join(sorted(missing))}")

    unknown = set(raw.keys()) - _VALID_TOP_KEYS
    if unknown:
        raise ValueError(
            f"{path}: unknown top-level key(s): {', '.join(sorted(unknown))}. "
            f"Valid keys: {', '.join(sorted(_VALID_TOP_KEYS))}"
        )


def _parse_target(target_cfg: dict, path: Path) -> dict[str, Any]:
    if "name" not in target_cfg:
        raise ValueError(f"{path}: target.name is required")

    chat_url = target_cfg.get("chat_url") or target_cfg.get("url")
    if not chat_url:
        raise ValueError(f"{path}: target.chat_url is required (or legacy target.url)")
    if not chat_url.startswith(("http://", "https://")):
        raise ValueError(f"{path}: target.chat_url must start with http:// or https://")

    reset_memory_url = target_cfg.get("reset_memory_url", "")
    if reset_memory_url and not reset_memory_url.startswith(("http://", "https://")):
        raise ValueError(f"{path}: target.reset_memory_url must start with http:// or https://")

    model = target_cfg.get("model", "")
    if not isinstance(model, str):
        raise ValueError(f"{path}: target.model must be a string")

    architecture_type = target_cfg.get("architecture_type", "")
    if not isinstance(architecture_type, str):
        raise ValueError(f"{path}: target.architecture_type must be a string")

    input_field = target_cfg.get("input_field", "prompt")
    if not isinstance(input_field, str) or not input_field.strip():
        raise ValueError(f"{path}: target.input_field must be a non-empty string")
    if "$INPUT" in input_field or any(ch in input_field for ch in "{}:\\"):
        raise ValueError(f"{path}: target.input_field must be a single input field name (ex: 'prompt')")

    output_field = target_cfg.get("output_field", "response")
    if not isinstance(output_field, str) or not output_field.strip():
        raise ValueError(f"{path}: target.output_field must be a non-empty string")

    return {
        "name": str(target_cfg["name"]),
        "chat_url": str(chat_url),
        "reset_memory_url": str(reset_memory_url),
        "model": model.strip(),
        "architecture_type": architecture_type.strip(),
        "input_field": str(input_field),
        "output_field": str(output_field),
    }


def _load_attacks(attacks_raw: Any, campaign_path: Path) -> tuple[Attack, ...]:
    refs = attacks_raw or []
    if not refs:
        raise ValueError(f"{campaign_path}: 'attacks' list must not be empty")

    attacks: list[Attack] = []
    for index, ref in enumerate(refs):
        if not isinstance(ref, str):
            raise ValueError(
                f"{campaign_path}: attacks[{index}] must be a file path (string), "
                f"got {type(ref).__name__}"
            )

        attack_path = Path(ref)
        if not attack_path.exists():
            attack_path = campaign_path.parent / ref
        if not attack_path.exists():
            raise FileNotFoundError(
                f"{campaign_path}: attacks[{index}] references '{ref}' — file not found. "
                f"Looked in: '{Path(ref).resolve()}' and '{(campaign_path.parent / ref).resolve()}'"
            )

        logger.debug("Loading attack[%d] from file: %s", index, attack_path)
        attacks.append(_build_attack(_read_yaml(attack_path), index, attack_path))

    return tuple(attacks)


def _build_attack(entry: dict[str, Any], index: int, path: Path) -> Attack:
    framework = entry.get("framework", "")
    valid_frameworks = list_framework_names()
    if framework not in valid_frameworks:
        raise ValueError(
            f"{path}: attacks[{index}].framework must be one of {valid_frameworks}, got '{framework}'"
        )

    intent = entry.get("intent", "")
    if not intent:
        raise ValueError(f"{path}: attacks[{index}].intent is required")

    plugin = get_plugin(framework)
    return plugin.build_attack(entry, index, path)


__all__ = ["load_campaign", "load_attack"]



