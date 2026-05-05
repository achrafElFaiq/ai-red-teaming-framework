from abc import ABC, abstractmethod

from core.models.attack import Attack
from core.models.attack_result import AttackResult
from core.models.attack_target import AttackTarget


class Runner(ABC):
    """Base contract for executing one attack against one target.

    A runner is backend-specific (e.g., PyRIT, Garak) and must return
    normalized framework results as a list of `AttackResult`.
    """

    @abstractmethod
    def run(self, target: AttackTarget, attack: Attack) -> list[AttackResult]:
        pass
