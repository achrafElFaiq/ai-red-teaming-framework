from .garak_runner import GarakRunner
from core.models.attack_target import AttackTarget
from core.models.attack import Attack

class GarakAttack(Attack):

    def __init__(self, intent: str, config: dict = None):
        super().__init__(intent=intent, framework="garak", config=config)


    def execute(self, target: AttackTarget):
        runner = GarakRunner()
        return runner.run(target, self)

