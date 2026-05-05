from dataclasses import dataclass

from core.models.attack import Attack


@dataclass(frozen=True)
class CampaignConfig:
    """
    Configuration object for an attack campaign.

    This structure defines what is required to execute a campaign:
    - `target_name`: human-readable name of the target
    - `target_chat_url`: HTTP/HTTPS endpoint used to send prompts
    - `target_reset_memory_url`: optional endpoint used to reset target state
    - `target_model`: optional target model name shown in reports/dashboard
    - `target_architecture_type`: optional target architecture type shown in reports/dashboard
    - `target_input_field`: input field name used for prompts (single JSON string field)
    - `target_output_field`: response JSON field that contains the model answer
    - `active_attacks`: list of attacks to execute against the target
    """
    target_name: str
    target_chat_url: str
    active_attacks: tuple[Attack, ...]
    campaign_name: str = ""
    target_reset_memory_url: str = ""
    target_model: str = ""
    target_architecture_type: str = ""
    target_input_field: str = "prompt"
    target_output_field: str = "response"

    @property
    def target_url(self) -> str:
        """Backward-compat alias for older call sites."""
        return self.target_chat_url

    def __post_init__(self):
        if not self.target_name.strip():
            raise ValueError("Campaign target_name must not be empty")
        if not self.target_chat_url.startswith(("http://", "https://")):
            raise ValueError("Campaign target_chat_url must start with http:// or https://")
        if self.target_reset_memory_url and not self.target_reset_memory_url.startswith(("http://", "https://")):
            raise ValueError("Campaign target_reset_memory_url must start with http:// or https://")
        if not isinstance(self.target_model, str):
            raise ValueError("Campaign target_model must be a string")
        if not isinstance(self.target_architecture_type, str):
            raise ValueError("Campaign target_architecture_type must be a string")
        if not self.target_input_field.strip():
            raise ValueError("Campaign target_input_field must not be empty")
        if "$INPUT" in self.target_input_field:
            raise ValueError("Campaign target_input_field must be a field name, not a JSON template")
        if any(ch in self.target_input_field for ch in "{}:\\"):
            raise ValueError("Campaign target_input_field must be a single input field name")
        if not self.target_output_field.strip():
            raise ValueError("Campaign target_output_field must not be empty")
        if not self.active_attacks:
            raise ValueError("Campaign active_attacks must not be empty")
