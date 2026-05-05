"""
Campaign Loader
===============
Parse a YAML campaign file and return a ready-to-run CampaignConfig.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from core.application.campaign_config import CampaignConfig
from core.models.attack import Attack
from frameworks.garak.garak_attack import GarakAttack
from frameworks.pyrit.pyrit_attack import PyritAttack

logger = logging.getLogger(__name__)

_REQUIRED_TOP_KEYS = {"target", "attacks"}
_VALID_TOP_KEYS = {"campaign", "target", "attacks"}
_VALID_FRAMEWORKS = {"pyrit", "garak"}



####################################################################
###                      Main method                             ###
####################################################################

def load_campaign(yaml_path: str | Path) -> CampaignConfig:
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Campaign file not found: {path}")

    # 1) Lire YAML campagne
    raw = _read_yaml(path)
    _validate_top_level(raw, path)

    # 2) Verifier target minimal
    target_cfg = _parse_target(raw["target"], path)

    # 3) Charger les fichiers d'attaque
    attacks = _load_attacks(raw.get("attacks"), path)

    # 4) Instancier PyritAttack / GarakAttack (fait dans _load_attacks)

    # 5) Retourner CampaignConfig
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





####################################################################
###                      Helper Methods                          ###
####################################################################



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
    if framework not in _VALID_FRAMEWORKS:
        raise ValueError(
            f"{path}: attacks[{index}].framework must be one of {sorted(_VALID_FRAMEWORKS)}, got '{framework}'"
        )

    intent = entry.get("intent", "")
    if not intent:
        raise ValueError(f"{path}: attacks[{index}].intent is required")

    if framework == "pyrit":
        return _build_pyrit_attack(entry, index, path)
    return _build_garak_attack(entry, index, path)


def _build_pyrit_attack(entry: dict[str, Any], index: int, path: Path) -> PyritAttack:
    orchestrator = entry.get("orchestrator", "")
    if not orchestrator:
        raise ValueError(f"{path}: attacks[{index}].orchestrator is required for pyrit attacks")

    objective = entry.get("objective", "")
    if not objective:
        raise ValueError(f"{path}: attacks[{index}].objective is required for pyrit attacks")

    config: dict[str, Any] = {
        "orchestrator": orchestrator,
        "objective": objective.strip(),
    }

    if "max_turns" in entry:
        config["max_turns"] = int(entry["max_turns"])

    if "prompts" in entry:
        prompts = entry["prompts"]
        if not isinstance(prompts, list) or not prompts:
            raise ValueError(f"{path}: attacks[{index}].prompts must be a non-empty list")
        config["prompts"] = prompts

    scoring = entry.get("scoring")
    if scoring:
        if not isinstance(scoring, dict):
            raise ValueError(f"{path}: attacks[{index}].scoring must be a mapping")
        config["scoring_question"] = _build_scoring_question(scoring, index, path)

    return PyritAttack(intent=entry["intent"], config=config)


def _build_garak_attack(entry: dict[str, Any], index: int, path: Path) -> GarakAttack:
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


def _build_scoring_question(scoring: dict[str, Any], index: int, path: Path):
    for key in ("true_description", "false_description", "category"):
        if key not in scoring:
            raise ValueError(f"{path}: attacks[{index}].scoring.{key} is required")

    from pyrit.score.true_false.self_ask_true_false_scorer import TrueFalseQuestion

    return TrueFalseQuestion(
        true_description=scoring["true_description"].strip(),
        false_description=scoring["false_description"].strip(),
        category=scoring["category"].strip(),
    )


__all__ = ["load_campaign", "load_attack"]
