from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from redteaming.domain.models.attack import Attack
from redteaming.domain.models.attack_result import AttackResult


class Runner(ABC):
    """Base contract for executing one attack against one target."""

    @abstractmethod
    def run(self, target: Any, attack: Attack) -> list[AttackResult]:
        raise NotImplementedError


