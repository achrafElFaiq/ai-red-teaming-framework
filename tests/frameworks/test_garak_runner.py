import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.models.attack import Attack
from core.models.attack_result import AttackResult
from core.models.attack_target import AttackTarget
from frameworks.garak.garak_runner import GarakRunner


class DummyTarget(AttackTarget):
    def __init__(self, input_field: str = "prompt", output_field: str = "response"):
        super().__init__(
            "Garak test target",
            "http://localhost:8000/api/chat",
            input_field=input_field,
            output_field=output_field,
        )

    def query(self, prompt: str):
        return "dummy response"

    def reset_history(self) -> None:
        pass


class DummyAttack(Attack):
    def __init__(self, config: dict | None = None):
        super().__init__(intent="probe", framework="garak", config=config or {"probe": "promptinject"})

    def execute(self, target: AttackTarget):  # pragma: no cover - not used in these tests
        raise NotImplementedError


class GarakRunnerTests(unittest.TestCase):
    def setUp(self):
        self.settings_patcher = patch(
            "frameworks.garak.garak_runner.get_runtime_settings",
            return_value=SimpleNamespace(
                garak_reports_dir="/tmp/garak",
                garak_config_path="config/garak_config.json",
                garak_request_timeout=60,
                garak_default_report_prefix="reports/run",
            ),
        )
        self.settings_patcher.start()

    def tearDown(self):
        self.settings_patcher.stop()

    def test_run_executes_garak_and_normalizes_report(self):
        runner = GarakRunner()
        target = DummyTarget()
        attack = DummyAttack({"probe": "promptinject", "report_prefix": "reports/custom_run"})
        expected_result = AttackResult(
            framework="garak",
            attack_name=attack.name,
            target_url=target.url,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            runner.garak_reports_dir = Path(tmp_dir)
            runner.config_path = Path(tmp_dir) / "garak_config.json"
            report_path = runner.garak_reports_dir / "custom_run.report.jsonl"
            report_path.write_text('{"dummy": true}\n', encoding="utf-8")

            with patch("frameworks.garak.garak_runner.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock, patch(
                "frameworks.garak.garak_runner.GarakNormalizer"
            ) as normalizer_cls:
                normalizer_cls.return_value.normalize.return_value = expected_result

                results = runner.run(target, attack)

        self.assertEqual(results, [expected_result])
        run_mock.assert_called_once()
        command = run_mock.call_args.args[0]
        self.assertEqual(command[0], "python")
        self.assertIn("--probes", command)
        self.assertIn("promptinject", command)
        self.assertIn("--report_prefix", command)
        self.assertIn("reports/custom_run", command)
        normalizer_cls.assert_called_once_with(report_path=str(report_path), target_url=target.url)

    def test_run_raises_runtime_error_when_garak_fails(self):
        runner = GarakRunner()
        target = DummyTarget()
        attack = DummyAttack()

        with tempfile.TemporaryDirectory() as tmp_dir:
            runner.garak_reports_dir = Path(tmp_dir)
            runner.config_path = Path(tmp_dir) / "garak_config.json"

            with patch("frameworks.garak.garak_runner.subprocess.run", return_value=SimpleNamespace(returncode=7)):
                with self.assertRaisesRegex(RuntimeError, "return code 7"):
                    runner.run(target, attack)

    def test_run_raises_when_report_is_missing(self):
        runner = GarakRunner()
        target = DummyTarget()
        attack = DummyAttack({"probe": "promptinject", "report_prefix": "reports/missing"})

        with tempfile.TemporaryDirectory() as tmp_dir:
            runner.garak_reports_dir = Path(tmp_dir)
            runner.config_path = Path(tmp_dir) / "garak_config.json"

            with patch("frameworks.garak.garak_runner.subprocess.run", return_value=SimpleNamespace(returncode=0)):
                with self.assertRaisesRegex(FileNotFoundError, "missing.report.jsonl"):
                    runner.run(target, attack)

    def test_write_generator_config_writes_expected_rest_payload(self):
        runner = GarakRunner()
        target = DummyTarget()
        attack = DummyAttack()

        with tempfile.TemporaryDirectory() as tmp_dir:
            runner.config_path = Path(tmp_dir) / "garak_config.json"
            runner._write_generator_config(target)

            config = json.loads(runner.config_path.read_text(encoding="utf-8"))

        generator = config["plugins"]["generators"]["rest"]["RestGenerator"]
        self.assertEqual(generator["uri"], target.url)
        self.assertEqual(generator["req_template"], '{"prompt": "$INPUT"}')
        self.assertTrue(generator["response_json"])
        self.assertEqual(generator["response_json_field"], "response")
        self.assertEqual(generator["request_timeout"], runner.settings.garak_request_timeout)
        self.assertEqual(generator["headers"], {"Content-Type": "application/json"})

    def test_write_generator_config_supports_custom_payload_fields(self):
        runner = GarakRunner()
        target = DummyTarget(
            input_field="message",
            output_field="answer",
        )
        attack = DummyAttack({"probe": "promptinject"})

        with tempfile.TemporaryDirectory() as tmp_dir:
            runner.config_path = Path(tmp_dir) / "garak_config.json"
            runner._write_generator_config(target)
            config = json.loads(runner.config_path.read_text(encoding="utf-8"))

        generator = config["plugins"]["generators"]["rest"]["RestGenerator"]
        self.assertEqual(generator["req_template"], '{"message": "$INPUT"}')
        self.assertEqual(generator["response_json_field"], "answer")


if __name__ == "__main__":
    unittest.main()

