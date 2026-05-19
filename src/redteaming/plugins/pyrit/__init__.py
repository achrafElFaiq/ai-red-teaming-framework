from __future__ import annotations

from pathlib import Path
from typing import Any

from redteaming.domain.models.attack import Attack
from redteaming.plugins.registry import FrameworkPlugin
from redteaming.plugins.pyrit.attack import PyritAttack


def build_attack(entry: dict[str, Any], index: int, path: Path) -> Attack:
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


PYRIT_PLUGIN = FrameworkPlugin(name="pyrit", build_attack=build_attack)

__all__ = ["PYRIT_PLUGIN", "PyritAttack", "build_attack"]


