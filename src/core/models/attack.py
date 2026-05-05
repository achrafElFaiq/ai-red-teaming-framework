from abc import ABC, abstractmethod
from typing import Any

from core.models.attack_result import AttackResult
from core.models.attack_target import AttackTarget


class Attack(ABC):
    """Base model for one executable attack scenario.

    Attributes:
    - `intent`: semantic identifier of the attack objective
    - `framework`: backend used to execute the attack (e.g. pyrit, garak)
    - `config`: framework-specific parameters used by the runner
    - `name`: human-readable derived name (`<framework> - <intent>`)
    """

    def __init__(self, intent: str, framework: str, config: dict[str, Any] | None = None):
        self.intent = intent
        self.framework = framework
        self.config = config or {}
        self.name = f"{self.framework} - {self.intent}"

    @abstractmethod
    def execute(self, target: AttackTarget) -> list[AttackResult]:
        """Execute this attack against a target and return normalized results."""
        pass
