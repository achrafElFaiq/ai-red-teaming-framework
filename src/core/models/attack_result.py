from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# ====================================================================
# AttackResult helper models (internal only)
# --------------------------------------------------------------------
# These models are not standalone business entities.
# They are only used to structure `AttackResult.prompts` and
# `AttackResult.conversation`.
# AttackResult (below) itself is the only model that should be used outside of this file.
# ====================================================================

class PromptResult(BaseModel):
    prompt: str
    response: str
    passed: bool
    score: Optional[float] = None
    rationale: Optional[str] = None
    detector: Optional[str] = None # Pour garak only


class ConversationTurn(BaseModel):
    turn: int
    prompt: str
    response: str
    score: bool
    rationale: Optional[str] = None


class Conversation(BaseModel):
    conversation_id : str
    objective: str
    achieved: bool
    turns: list[ConversationTurn]

# ====================================================================
# End of AttackResult helper models
# ====================================================================


class AttackResult(BaseModel):
    """Normalized result produced by one backend attack execution.

    A result always contains framework metadata (`framework`, `attack_name`,
    `target_url`, `timestamp`) and exactly one payload shape depending on
    the backend:
    - `prompts` for Garak-style prompt-by-prompt scans
    - `conversation` for PyRIT-style multi-turn attacks
    """
    framework: str
    attack_name: str
    target_url: str
    campaign_name: str = ""
    target_model: str = ""
    target_architecture_type: str = ""
    timestamp: datetime = datetime.now()

    # garak — flat list of independent prompts
    prompts: Optional[list[PromptResult]] = None

    # pyrit — one single conversation
    conversation: Optional[Conversation] = None

    def save(self, path: str):
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=2))
