from redteaming.domain.models.attack import Attack
from redteaming.infrastructure.http_attack_target import AttackTarget

from .runner import PyritRunner


class PyritAttack(Attack):
    def __init__(self, intent: str, config: dict = None):
        super().__init__(intent=intent, framework="pyrit", config=config)

    def execute(self, target: AttackTarget):
        runner = PyritRunner()
        return runner.run(target, self)


