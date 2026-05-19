from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from redteaming.domain.models.attack_result import AttackResult


class Attack(ABC):
    """Base model for one executable attack scenario."""

    def __init__(self, intent: str, framework: str, config: dict[str, Any] | None = None):
        self.intent = intent
        self.framework = framework
        self.config = config or {}
        self.name = f"{self.framework} - {self.intent}"

    @abstractmethod
    def execute(self, target: Any) -> list[AttackResult]:
        """Execute this attack against a target and return normalized results."""
        raise NotImplementedError


