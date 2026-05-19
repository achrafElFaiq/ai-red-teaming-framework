from redteaming.domain.models.attack import Attack
from redteaming.infrastructure.http_attack_target import AttackTarget

from .runner import GarakRunner


class GarakAttack(Attack):
    def __init__(self, intent: str, config: dict = None):
        super().__init__(intent=intent, framework="garak", config=config)

    def execute(self, target: AttackTarget):
        runner = GarakRunner()
        return runner.run(target, self)


