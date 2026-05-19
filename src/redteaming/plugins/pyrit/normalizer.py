"""Convert PyRIT attack results into the framework AttackResult format."""

from datetime import datetime
import logging

from pyrit.memory.central_memory import CentralMemory
from pyrit.models.attack_result import AttackOutcome
from pyrit.models.attack_result import AttackResult as PyritAttackResult

from redteaming.domain.contracts.normalizer import Normalizer
from redteaming.domain.models.attack_result import AttackResult, Conversation, ConversationTurn

logger = logging.getLogger(__name__)


class PyritNormalizer(Normalizer):
    def __init__(self, pyrit_result: PyritAttackResult, target_url: str, attack_name: str):
        self.pyrit_result = pyrit_result
        self.target_url = target_url
        self.attack_name = attack_name

    def normalize(self) -> AttackResult:
        memory = CentralMemory.get_memory_instance()

        active_ids = list(self.pyrit_result.get_active_conversation_ids())
        if not active_ids:
            logger.warning("No active conversation id found during PyRIT normalization for attack '%s'", self.attack_name)
            return self._build_empty_result()

        turns = []
        turn_number = 1

        for conv_id in active_ids:
            pieces = memory.get_message_pieces(conversation_id=conv_id)
            pieces_sorted = sorted(pieces, key=lambda p: p.sequence)

            i = 0
            while i < len(pieces_sorted) - 1:
                user_piece = pieces_sorted[i]
                assistant_piece = pieces_sorted[i + 1]

                if user_piece.role == "user" and assistant_piece.role == "assistant":
                    score = False
                    rationale = "No score found."

                    scores = memory.get_prompt_scores(prompt_ids=[assistant_piece.id])
                    if scores:
                        score = bool(scores[0].get_value())
                        rationale = scores[0].score_rationale

                    turns.append(ConversationTurn(
                        turn=turn_number,
                        prompt=user_piece.original_value,
                        response=assistant_piece.original_value,
                        score=score,
                        rationale=rationale,
                    ))
                    turn_number += 1
                    i += 2
                else:
                    i += 1

        conversation = Conversation(
            conversation_id=self.pyrit_result.conversation_id,
            objective=self.pyrit_result.objective,
            achieved=self.pyrit_result.outcome == AttackOutcome.SUCCESS,
            turns=turns,
        )

        return AttackResult(
            framework="pyrit",
            attack_name=self.attack_name,
            target_url=self.target_url,
            timestamp=datetime.now(),
            conversation=conversation,
        )

    def _build_empty_result(self) -> AttackResult:
        return AttackResult(
            framework="pyrit",
            attack_name=self.attack_name,
            target_url=self.target_url,
            timestamp=datetime.now(),
            conversation=Conversation(
                conversation_id=self.pyrit_result.conversation_id,
                objective=self.pyrit_result.objective,
                achieved=False,
                turns=[],
            ),
        )


