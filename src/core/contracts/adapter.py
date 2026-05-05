from abc import ABC, abstractmethod
from typing import Any

from core.models.attack_target import AttackTarget


class Adapter(ABC):
    """Base contract for framework-to-runner target adaptation.

    An adapter receives a framework `AttackTarget` and returns the target
    object format expected by a specific backend runner.
    """

    @abstractmethod
    def wrap(self, target: AttackTarget) -> Any:
        pass
