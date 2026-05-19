import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from redteaming.domain.models.attack_result import AttackResult

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = PROJECT_ROOT / "schemas"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _validator(schema_name: str) -> Draft202012Validator:
    schema = _load_json(SCHEMAS_DIR / schema_name)
    return Draft202012Validator(schema)


def _assert_valid(schema_name: str, payload) -> None:
    errors = sorted(_validator(schema_name).iter_errors(payload), key=lambda err: err.json_path)
    assert not errors, "\n".join(f"{error.json_path}: {error.message}" for error in errors)


def _assert_invalid(schema_name: str, payload) -> None:
    errors = list(_validator(schema_name).iter_errors(payload))
    assert errors, f"Expected invalid payload for {schema_name}"


def test_campaign_schema_accepts_reference_campaigns_and_template():
    for path in [
        PROJECT_ROOT / "examples" / "templates" / "campaign.yaml",
        PROJECT_ROOT / "examples" / "campaigns" / "R1-prompt-leakage" / "prompt_leakage.yaml",
        PROJECT_ROOT / "examples" / "campaigns" / "R5-indirect-prompt-injection" / "indirect_prompt_injection.yaml",
    ]:
        _assert_valid("campaign.schema.json", _load_yaml(path))


def test_campaign_schema_rejects_missing_attacks():
    _assert_invalid(
        "campaign.schema.json",
        {
            "target": {
                "name": "Bot",
                "chat_url": "http://localhost:8000/api/chat",
            }
        },
    )


def test_attack_schema_accepts_reference_attacks_and_templates():
    for path in [
        PROJECT_ROOT / "examples" / "templates" / "attack_pyrit_dataset.yaml",
        PROJECT_ROOT / "examples" / "templates" / "attack_garak.yaml",
        PROJECT_ROOT / "examples" / "attacks" / "R1-prompt-leakage" / "r1_pyrit_direct_request.yaml",
        PROJECT_ROOT / "examples" / "attacks" / "R1-prompt-leakage" / "r1_pyrit_multi_turn_escalation.yaml",
    ]:
        _assert_valid("attack.schema.json", _load_yaml(path))


def test_attack_schema_rejects_garak_transport_fields():
    _assert_invalid(
        "attack.schema.json",
        {
            "framework": "garak",
            "intent": "bad_probe",
            "probe": "promptinject",
            "req_template": "{\"prompt\": \"$INPUT\"}",
        },
    )


def test_report_schema_accepts_phase0_baseline_report_fixtures():
    for path in [
        PROJECT_ROOT / "tests" / "fixtures" / "reports" / "pyrit_attack_result_baseline.json",
        PROJECT_ROOT / "tests" / "fixtures" / "reports" / "garak_attack_result_baseline.json",
    ]:
        _assert_valid("report.schema.json", _load_json(path))


def test_report_schema_accepts_current_model_dump_shape():
    payload = AttackResult(
        framework="dummy",
        attack_name="attack-smoke",
        target_url="http://localhost:8000/api/chat",
    ).model_dump(mode="json")
    _assert_valid("report.schema.json", payload)


def test_report_schema_rejects_missing_framework():
    _assert_invalid(
        "report.schema.json",
        {
            "attack_name": "attack-smoke",
            "target_url": "http://localhost:8000/api/chat",
            "campaign_name": "",
            "campaign_run_id": "",
            "campaign_run_timestamp": None,
            "target_model": "",
            "target_architecture_type": "",
            "timestamp": "2026-05-18T10:00:00",
            "prompts": None,
            "conversation": None,
        },
    )

