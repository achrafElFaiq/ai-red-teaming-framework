from abc import ABC, abstractmethod
from core.models.attack_result import AttackResult


class Normalizer(ABC):
    """Base contract for converting backend-specific outputs into `AttackResult`."""

    @abstractmethod
    def normalize(self) -> AttackResult:
        pass
