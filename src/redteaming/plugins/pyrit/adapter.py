"""Wrap the framework AttackTarget into a PyRIT-compatible PromptTarget."""

import logging

from pyrit.models.message import Message
from pyrit.models.message_piece import MessagePiece
from pyrit.prompt_target.common.prompt_target import PromptTarget
from pyrit.prompt_target.common.target_capabilities import TargetCapabilities

from redteaming.domain.contracts.adapter import Adapter
from redteaming.infrastructure.http_attack_target import AttackTarget

logger = logging.getLogger(__name__)


class _WrappedPromptTarget(PromptTarget):
    def __init__(self, wrapped_target: AttackTarget, *args, **kwargs):
        caps = TargetCapabilities(
            supports_multi_turn=True,
            supports_multi_message_pieces=True,
        )
        super().__init__(*args, custom_capabilities=caps, **kwargs)
        self._wrapped_target = wrapped_target
        self._turn_counter = 0

    @property
    def supports_multi_turn(self) -> bool:
        return True

    def reset_history(self) -> None:
        self._wrapped_target.reset_history()
        self._turn_counter = 0

    async def send_prompt_async(self, *, message: Message) -> list[Message]:
        user_piece = message.message_pieces[0]
        prompt = user_piece.converted_value

        self._turn_counter += 1
        prompt_preview = prompt[:120].replace("\n", " ")
        logger.info("[Turn %d] (Attacker) -> %s", self._turn_counter, prompt_preview)

        response = self._wrapped_target.query(prompt) or ""

        response_preview = response[:120].replace("\n", " ")
        logger.info("[Turn %d] (Target)  -> %s", self._turn_counter, response_preview)

        response_piece = MessagePiece(
            role="assistant",
            original_value=response,
            converted_value=response,
            conversation_id=user_piece.conversation_id,
            sequence=user_piece.sequence + 1,
        )
        return [Message(message_pieces=[response_piece])]


class PyritAdapter(Adapter):
    def wrap(self, target: AttackTarget) -> PromptTarget:
        return _WrappedPromptTarget(wrapped_target=target, endpoint=target.url)

