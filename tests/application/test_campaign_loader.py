"""Tests for core.application.campaign_loader."""

import textwrap
from pathlib import Path

import pytest

from core.application.campaign_loader import load_campaign, load_attack


@pytest.fixture
def tmp_yaml(tmp_path):
    """Helper that writes YAML content to a temp file and returns its path."""
    def _write(content: str, name: str = "campaign.yaml") -> Path:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(content), encoding="utf-8")
        return p
    return _write


def _write_attack(tmp_path, subdir, filename, content):
    """Helper: write an attack YAML into a subdirectory."""
    d = tmp_path / subdir
    d.mkdir(parents=True, exist_ok=True)
    p = d / filename
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


# ═════════════════════════════════════════════════════════════════
# Campaign with file references
# ═════════════════════════════════════════════════════════════════

def test_load_campaign_with_garak_file(tmp_yaml, tmp_path):
    """Campaign referencing a Garak attack file loads correctly."""
    _write_attack(tmp_path, "attacks", "blank.yaml", """
        framework: garak
        intent: blank_probe
        probe: test.Blank
    """)
    campaign = tmp_yaml("""
        target:
          name: TestBot
          url: http://localhost:8000/api/chat
        attacks:
          - attacks/blank.yaml
    """)
    config = load_campaign(campaign)
    assert config.target_name == "TestBot"
    assert len(config.active_attacks) == 1
    assert config.active_attacks[0].framework == "garak"
    assert config.active_attacks[0].intent == "blank_probe"
    assert config.active_attacks[0].config["probe"] == "test.Blank"


def test_load_campaign_with_pyrit_crescendo(tmp_yaml, tmp_path):
    """Campaign referencing a PyRIT crescendo attack with scoring."""
    _write_attack(tmp_path, "attacks", "crescendo.yaml", """
        framework: pyrit
        intent: test_attack
        orchestrator: crescendo
        max_turns: 5
        objective: "Test objective"
        scoring:
          true_description: "Leaked info"
          false_description: "Did not leak"
          category: test_cat
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api/chat
        attacks:
          - attacks/crescendo.yaml
    """)
    config = load_campaign(campaign)
    attack = config.active_attacks[0]
    assert attack.config["orchestrator"] == "crescendo"
    assert attack.config["max_turns"] == 5
    sq = attack.config["scoring_question"]
    assert sq.true_description == "Leaked info"
    assert sq.category == "test_cat"


def test_load_campaign_with_pyrit_dataset(tmp_yaml, tmp_path):
    """Campaign referencing a PyRIT dataset attack with prompts list."""
    _write_attack(tmp_path, "attacks", "dataset.yaml", """
        framework: pyrit
        intent: scan
        orchestrator: dataset
        objective: scan
        prompts:
          - "Question 1"
          - "Question 2"
        scoring:
          true_description: td
          false_description: fd
          category: cat
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api/chat
        attacks:
          - attacks/dataset.yaml
    """)
    config = load_campaign(campaign)
    assert config.active_attacks[0].config["prompts"] == ["Question 1", "Question 2"]


def test_load_campaign_multiple_files(tmp_yaml, tmp_path):
    """Campaign with multiple attack file references loads in order."""
    _write_attack(tmp_path, "attacks", "pyrit.yaml", """
        framework: pyrit
        intent: a1
        orchestrator: red_teaming
        objective: obj
        scoring:
          true_description: t
          false_description: f
          category: c
    """)
    _write_attack(tmp_path, "attacks", "garak.yaml", """
        framework: garak
        intent: a2
        probe: test.Blank
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api/chat
        attacks:
          - attacks/pyrit.yaml
          - attacks/garak.yaml
    """)
    config = load_campaign(campaign)
    assert len(config.active_attacks) == 2
    assert config.active_attacks[0].framework == "pyrit"
    assert config.active_attacks[1].framework == "garak"



# ═════════════════════════════════════════════════════════════════
# load_attack (standalone)
# ═════════════════════════════════════════════════════════════════

def test_load_single_attack_file(tmp_yaml):
    path = tmp_yaml("""
        framework: garak
        intent: standalone_probe
        probe: test.Blank
        report_prefix: reports/standalone
    """, name="standalone.yaml")
    attack = load_attack(path)
    assert attack.framework == "garak"
    assert attack.intent == "standalone_probe"
    assert attack.config["probe"] == "test.Blank"


def test_load_single_attack_file_not_found():
    with pytest.raises(FileNotFoundError, match="Attack file not found"):
        load_attack("/nonexistent/attack.yaml")


# ═════════════════════════════════════════════════════════════════
# Validation errors
# ═════════════════════════════════════════════════════════════════

def test_file_reference_not_found(tmp_yaml):
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api/chat
        attacks:
          - nonexistent/attack.yaml
    """)
    with pytest.raises(FileNotFoundError, match="file not found"):
        load_campaign(campaign)


def test_non_string_entry_rejected(tmp_yaml):
    """A non-string entry in attacks list raises ValueError."""
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api/chat
        attacks:
          - 42
    """)
    with pytest.raises(ValueError, match="must be a file path"):
        load_campaign(campaign)


def test_inline_dict_rejected(tmp_yaml):
    """An inline dict in attacks list is rejected — must be a file path."""
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api/chat
        attacks:
          - framework: garak
            intent: x
            probe: test.Blank
    """)
    with pytest.raises(ValueError, match="must be a file path"):
        load_campaign(campaign)


def test_missing_target(tmp_yaml):
    campaign = tmp_yaml("""
        attacks:
          - some_file.yaml
    """)
    with pytest.raises(ValueError, match="missing required top-level key.*target"):
        load_campaign(campaign)


def test_missing_attacks(tmp_yaml):
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api
    """)
    with pytest.raises(ValueError, match="missing required top-level key.*attacks"):
        load_campaign(campaign)


def test_empty_attacks_list(tmp_yaml):
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api
        attacks: []
    """)
    with pytest.raises(ValueError, match="must not be empty"):
        load_campaign(campaign)


def test_unknown_framework_in_attack_file(tmp_yaml, tmp_path):
    _write_attack(tmp_path, "attacks", "bad.yaml", """
        framework: unknown
        intent: x
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api
        attacks:
          - attacks/bad.yaml
    """)
    with pytest.raises(ValueError, match="framework must be one of"):
        load_campaign(campaign)


def test_missing_intent_in_attack_file(tmp_yaml, tmp_path):
    _write_attack(tmp_path, "attacks", "bad.yaml", """
        framework: garak
        probe: test.Blank
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api
        attacks:
          - attacks/bad.yaml
    """)
    with pytest.raises(ValueError, match="intent is required"):
        load_campaign(campaign)


def test_pyrit_missing_orchestrator_in_attack_file(tmp_yaml, tmp_path):
    _write_attack(tmp_path, "attacks", "bad.yaml", """
        framework: pyrit
        intent: x
        objective: obj
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api
        attacks:
          - attacks/bad.yaml
    """)
    with pytest.raises(ValueError, match="orchestrator is required"):
        load_campaign(campaign)


def test_garak_missing_probe_in_attack_file(tmp_yaml, tmp_path):
    _write_attack(tmp_path, "attacks", "bad.yaml", """
        framework: garak
        intent: x
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api
        attacks:
          - attacks/bad.yaml
    """)
    with pytest.raises(ValueError, match="probe is required"):
        load_campaign(campaign)


def test_campaign_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_campaign("/nonexistent/path.yaml")


def test_unknown_top_level_key(tmp_yaml):
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api
        attacks:
          - some.yaml
        extra_key: bad
    """)
    with pytest.raises(ValueError, match="unknown top-level key"):
        load_campaign(campaign)


def test_target_chat_url_and_optional_reset_memory_url(tmp_yaml, tmp_path):
    _write_attack(tmp_path, "attacks", "g.yaml", """
        framework: garak
        intent: probe
        probe: test.Blank
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          model: llama3.1
          architecture_type: RAG-connected bot
          chat_url: http://localhost:8000/api/chat
          reset_memory_url: http://localhost:8000/api/reset
        attacks:
          - attacks/g.yaml
    """)
    config = load_campaign(campaign)
    assert config.target_chat_url == "http://localhost:8000/api/chat"
    assert config.target_reset_memory_url == "http://localhost:8000/api/reset"
    assert config.target_model == "llama3.1"
    assert config.target_architecture_type == "RAG-connected bot"


def test_target_model_and_architecture_type_default_to_empty_strings(tmp_yaml, tmp_path):
    _write_attack(tmp_path, "attacks", "g.yaml", """
        framework: garak
        intent: probe
        probe: test.Blank
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          chat_url: http://localhost:8000/api/chat
        attacks:
          - attacks/g.yaml
    """)
    config = load_campaign(campaign)
    assert config.target_model == ""
    assert config.target_architecture_type == ""


def test_target_legacy_url_is_still_supported(tmp_yaml, tmp_path):
    _write_attack(tmp_path, "attacks", "g.yaml", """
        framework: garak
        intent: probe
        probe: test.Blank
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          url: http://localhost:8000/api/chat
        attacks:
          - attacks/g.yaml
    """)
    config = load_campaign(campaign)
    assert config.target_chat_url == "http://localhost:8000/api/chat"
    assert config.target_url == "http://localhost:8000/api/chat"


def test_invalid_reset_memory_url_rejected(tmp_yaml, tmp_path):
    _write_attack(tmp_path, "attacks", "g.yaml", """
        framework: garak
        intent: probe
        probe: test.Blank
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          chat_url: http://localhost:8000/api/chat
          reset_memory_url: ftp://localhost/reset
        attacks:
          - attacks/g.yaml
    """)
    with pytest.raises(ValueError, match="target.reset_memory_url must start with http:// or https://"):
        load_campaign(campaign)


def test_target_transport_template_and_response_field(tmp_yaml, tmp_path):
    _write_attack(tmp_path, "attacks", "garak_custom.yaml", """
        framework: garak
        intent: custom_probe
        probe: promptinject
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          chat_url: http://localhost:8000/api/chat
          input_field: message
          output_field: answer
        attacks:
          - attacks/garak_custom.yaml
    """)
    config = load_campaign(campaign)
    assert config.target_input_field == "message"
    assert config.target_output_field == "answer"


def test_target_input_field_must_be_single_field_name(tmp_yaml, tmp_path):
    _write_attack(tmp_path, "attacks", "garak_bad.yaml", """
        framework: garak
        intent: bad_probe
        probe: promptinject
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          chat_url: http://localhost:8000/api/chat
          input_field: '{"message": "$INPUT"}'
        attacks:
          - attacks/garak_bad.yaml
    """)
    with pytest.raises(ValueError, match="target.input_field must be a single input field name"):
        load_campaign(campaign)


def test_garak_attack_rejects_transport_keys(tmp_yaml, tmp_path):
    _write_attack(tmp_path, "attacks", "garak_bad.yaml", """
        framework: garak
        intent: bad_probe
        probe: promptinject
        req_template: message
    """)
    campaign = tmp_yaml("""
        target:
          name: Bot
          chat_url: http://localhost:8000/api/chat
        attacks:
          - attacks/garak_bad.yaml
    """)
    with pytest.raises(ValueError, match="must be configured in campaign.target"):
        load_campaign(campaign)
