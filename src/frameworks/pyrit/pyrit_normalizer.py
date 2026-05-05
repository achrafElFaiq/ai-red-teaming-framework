"""
PyritNormalizer — Converts PyRIT attack results into the framework's internal AttackResult format.
==================================================================================================

Pipeline:
  1. Retrieve active conversation IDs from the raw PyritAttackResult.
  2. For each conversation, fetch message pieces from PyRIT's central SQLite memory store.
  3. Iterate user/assistant pairs → extract score (breach detected?) + rationale → build ConversationTurns.
  4. Wrap turns into a Conversation (objective, achieved, turns), then into a standard AttackResult.

Edge cases:
  - No active conversation IDs → returns an empty result (achieved=False, no turns).
  - _clear_db() (commented out) can wipe PyRIT's SQLite tables between runs to avoid state pollution.

Output: A framework-agnostic AttackResult, ready to be stored by JsonReportStore and rendered in RedTeaming Framework.
"""

from datetime import datetime
import logging
import sqlite3

from pyrit.memory.central_memory import CentralMemory
from pyrit.models.attack_result import AttackResult as PyritAttackResult
from pyrit.models.attack_result import AttackOutcome

from core.contracts.normalizer import Normalizer
from core.models.attack_result import AttackResult, Conversation, ConversationTurn


logger = logging.getLogger(__name__)

class PyritNormalizer(Normalizer):

    def __init__(self, pyrit_result: PyritAttackResult,
                 db_path: str, target_url: str, attack_name: str):
        self.pyrit_result = pyrit_result
        self.db_path = db_path
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
                    rationale = "Aucun score trouvé."

                    scores = memory.get_prompt_scores(prompt_ids=[assistant_piece.id])
                    if scores:
                        score = scores[0].get_value() == True
                        rationale = scores[0].score_rationale

                    turns.append(ConversationTurn(
                        turn=turn_number,
                        prompt=user_piece.original_value,
                        response=assistant_piece.original_value,
                        score=score,
                        rationale=rationale
                    ))
                    turn_number += 1
                    i += 2
                else:
                    i += 1

        #self._clear_db()

        conversation = Conversation(
            conversation_id=self.pyrit_result.conversation_id,
            objective=self.pyrit_result.objective,
            achieved=self.pyrit_result.outcome == AttackOutcome.SUCCESS,
            turns=turns
        )


        return AttackResult(
            framework="pyrit",
            attack_name=self.attack_name,
            target_url=self.target_url,
            timestamp=datetime.now(),
            conversation=conversation
        )

    def _build_empty_result(self) -> AttackResult:
        result = AttackResult(
            framework="pyrit",
            attack_name=self.attack_name,
            target_url=self.target_url,
            timestamp=datetime.now(),
            conversation=Conversation(
                conversation_id=self.pyrit_result.conversation_id,
                objective=self.pyrit_result.objective,
                achieved=False,
                turns=[]
            )
        )
        #self._clear_db()
        return result


    def _clear_db(self):
        logger.debug("Cleaning PyRIT database at %s", self.db_path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM PromptMemoryEntries")
            cursor.execute("DELETE FROM ScoreEntries")
            cursor.execute("DELETE FROM AttackResultEntries")
            conn.commit()
            logger.debug("PyRIT database tables cleared successfully")
        except Exception as e:
            logger.error("Failed to clean PyRIT database: %s", e)
        finally:
            conn.close()
