from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PromptResult(BaseModel):
    prompt: str
    response: str
    passed: bool
    score: Optional[float] = None
    rationale: Optional[str] = None
    detector: Optional[str] = None


class ConversationTurn(BaseModel):
    turn: int
    prompt: str
    response: str
    score: bool
    rationale: Optional[str] = None


class Conversation(BaseModel):
    conversation_id: str
    objective: str
    achieved: bool
    turns: list[ConversationTurn]


class AttackResult(BaseModel):
    """Normalized result produced by one backend attack execution."""

    framework: str
    attack_name: str
    target_url: str
    campaign_name: str = ""
    campaign_run_id: str = ""
    campaign_run_timestamp: Optional[datetime] = None
    target_model: str = ""
    target_architecture_type: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)

    prompts: Optional[list[PromptResult]] = None
    conversation: Optional[Conversation] = None

    def save(self, path: str):
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=2))

