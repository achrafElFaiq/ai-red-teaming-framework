import json
import logging
import subprocess
import sys
from pathlib import Path

from redteaming.settings import get_runtime_settings
from redteaming.domain.contracts.runner import Runner
from redteaming.domain.models.attack import Attack
from redteaming.domain.models.attack_result import AttackResult
from redteaming.infrastructure.http_attack_target import AttackTarget
from redteaming.plugins.garak.normalizer import GarakNormalizer

logger = logging.getLogger(__name__)


class GarakRunner(Runner):
    """Run Garak attacks and normalize the generated report into framework results."""

    _DEFAULT_INPUT_FIELD = "prompt"
    _DEFAULT_OUTPUT_FIELD = "response"

    def __init__(self):
        self.settings = get_runtime_settings(frameworks={"garak"})
        self.garak_reports_dir = Path(self.settings.garak.garak_reports_dir)
        self.config_path = Path(self.settings.garak.garak_config_path)

    def run(self, target: AttackTarget, attack: Attack) -> list[AttackResult]:
        probe = attack.config.get("probe", "?")
        logger.info(
            "[Garak] Starting probe '%s' against %s",
            probe, target.url,
        )
        self._write_generator_config(target)
        self._ensure_reports_dir()
        report_prefix = self._resolve_report_prefix(attack)
        command = self._build_garak_command(target, attack, report_prefix)
        self._execute_garak(command, attack)
        report_path = self._resolve_report_path(report_prefix)
        return self._normalize_report(report_path, target, attack)

    def _write_generator_config(self, target: AttackTarget) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        input_field = getattr(target, "input_field", self._DEFAULT_INPUT_FIELD) or self._DEFAULT_INPUT_FIELD
        output_field = getattr(target, "output_field", self._DEFAULT_OUTPUT_FIELD)
        req_template = json.dumps({input_field: "$INPUT"})
        config = {
            "plugins": {
                "generators": {
                    "rest": {
                        "RestGenerator": {
                            "uri": target.url,
                            "req_template": req_template,
                            "response_json": True,
                            "response_json_field": output_field,
                            "request_timeout": self.settings.garak.garak_request_timeout,
                            "headers": {
                                "Content-Type": "application/json"
                            }
                        }
                    }
                }
            }
        }
        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.debug("Generated Garak REST config at %s", self.config_path)

    def _ensure_reports_dir(self) -> None:
        self.garak_reports_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_report_prefix(self, attack: Attack) -> str:
        return attack.config.get("report_prefix", self.settings.garak.garak_default_report_prefix)

    def _build_garak_command(self, target: AttackTarget, attack: Attack, report_prefix: str) -> list[str]:
        return [
            sys.executable,
            "-m",
            "garak",
            "--target_type",
            "rest",
            "--target_name",
            target.url,
            "--config",
            str(self.config_path),
            "--probes",
            attack.config.get("probe"),
            "--report_prefix",
            report_prefix,
        ]

    def _execute_garak(self, command: list[str], attack: Attack) -> None:
        result = subprocess.run(
            command,
            capture_output=False,
            text=True,
        )

        if result.returncode != 0:
            logger.error(
                "[Garak] Subprocess failed (exit code %d) for attack '%s'",
                result.returncode, attack.name,
            )
            raise RuntimeError(f"Garak execution failed with return code {result.returncode}")

        logger.info("[Garak] Subprocess completed successfully for attack '%s'", attack.name)

    def _resolve_report_path(self, report_prefix: str) -> Path:
        stem = Path(report_prefix).name
        report_path = self.garak_reports_dir / f"{stem}.report.jsonl"
        logger.debug("Looking for Garak raw report at %s", report_path)
        return report_path

    def _normalize_report(self, report_path: Path, target: AttackTarget, attack: Attack) -> list[AttackResult]:
        if report_path.exists():
            normalizer = GarakNormalizer(
                report_path=str(report_path),
                target_url=target.url,
            )
            attack_result = normalizer.normalize()
            logger.info("Garak attack '%s' produced 1 normalized result", attack.name)
            return [attack_result]

        logger.error("Garak raw report was not found for attack '%s'", attack.name)
        raise FileNotFoundError(f"Garak report file not found at {report_path}")

