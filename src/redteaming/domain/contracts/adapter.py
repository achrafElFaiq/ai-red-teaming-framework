from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Adapter(ABC):
    """Base contract for framework-to-runner target adaptation."""

    @abstractmethod
    def wrap(self, target: Any) -> Any:
        raise NotImplementedError


