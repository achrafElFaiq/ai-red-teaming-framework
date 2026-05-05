"""
RedTeaming Framework
====================

Usage::

    python main.py <campaign.yaml>
    python main.py examples/campaigns/use_cases/use_case1/smoke_test.yaml --log-level DEBUG
    python main.py examples/campaigns/use_cases/use_case1/smoke_test.yaml --skip-checks
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

# ── Add src/ to import path ───────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from core.application.campaign_loader import load_campaign
from core.application.health_check import run_preflight_checks
from core.models.attack_target import AttackTarget
from core.orchestration.attack_orchestrator import AttackOrchestrator

DASHBOARD_PATH = _SRC_DIR / "core" / "results" / "report_viewer.py"


def _configure_logging(level: str) -> None:
    """Set up framework logging and silence noisy third-party loggers."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    for noisy in (
        "pyrit.memory", "pyrit.prompt_target", "pyrit.executor",
        "pyrit.score", "pyrit.exceptions",
        "httpx", "httpcore", "asyncio",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Replace verbose PyRIT scorer retry errors with a one-liner
    logging.getLogger("pyrit.exceptions.exceptions_helpers").addFilter(_ScorerRetryFilter())


class _ScorerRetryFilter(logging.Filter):
    """Collapse PyRIT scorer retry stack traces into a single readable line."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "objective scorer" in msg and "Invalid JSON" in msg:
            attempt = "?"
            if "Retry attempt " in msg:
                attempt = msg.split("Retry attempt ")[1].split(" ")[0]
            record.msg = (
                "[Scorer] ⚠ Retry #%s — LLM returned invalid JSON "
                "(scorer model may not support structured output reliably)"
            )
            record.args = (attempt,)
        return True


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="RedTeaming Framework",
        description="Run a red teaming campaign from a YAML configuration file.",
    )
    parser.add_argument(
        "campaign",
        help="Path to the campaign YAML file (e.g. campaigns/smoke_test.yaml)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Skip automatic dashboard launch after the campaign",
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip pre-flight health checks (target, LLMs, DB)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.log_level)

    logger = logging.getLogger("RedTeaming Framework")

    # ── Load campaign ──────────────────────────────────────────
    try:
        config = load_campaign(args.campaign)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Failed to load campaign: %s", exc)
        return 1

    logger.info("─" * 60)
    logger.info("[Config] Campaign  : %s", config.campaign_name or args.campaign)
    logger.info("[Config] Target    : %s → %s", config.target_name, config.target_chat_url)
    if config.target_model:
        logger.info("[Config] Target model : %s", config.target_model)
    if config.target_architecture_type:
        logger.info("[Config] Target architecture : %s", config.target_architecture_type)
    if config.target_reset_memory_url:
        logger.info("[Config] Target reset URL : %s", config.target_reset_memory_url)
    else:
        logger.info("[Config] Target reset URL : (disabled)")
    logger.info("[Config] Target input field : %s", config.target_input_field)
    logger.info("[Config] Target output field: %s", config.target_output_field)
    logger.info("[Config] Attacks   : %d", len(config.active_attacks))
    for i, atk in enumerate(config.active_attacks, 1):
        mode = atk.config.get("orchestrator", atk.config.get("probe", "?"))
        logger.info("[Config]   %d. [%s] %s (%s)", i, atk.framework, atk.intent, mode)
    logger.info("─" * 60)

    # ── Pre-flight health checks ──────────────────────────────
    if not args.skip_checks:
        issues = run_preflight_checks(config)
        if issues:
            logger.error("─" * 60)
            logger.error("[Preflight] Campaign aborted — fix the issues below:")
            for issue in issues:
                logger.error("[Preflight]   ✗ %s", issue)
            logger.error("─" * 60)
            logger.error("[Preflight] Use --skip-checks to bypass pre-flight checks")
            return 1
    else:
        logger.info("[Preflight] Skipped (--skip-checks)")

    # ── Build orchestrator ─────────────────────────────────────
    target = AttackTarget(
        config.target_name,
        config.target_chat_url,
        config.target_reset_memory_url or None,
        config.target_input_field,
        config.target_output_field,
        config.target_model,
        config.target_architecture_type,
    )
    orchestrator = AttackOrchestrator(
        target=target,
        campaign_name=config.campaign_name,
    )
    for attack in config.active_attacks:
        orchestrator.add_attack(attack)

    # ── Execute ────────────────────────────────────────────────
    orchestrator.execute_attacks()

    # ── Summary ────────────────────────────────────────────────
    summary = orchestrator.summary()
    print("\n" + "=" * 60)
    print("  CAMPAIGN SUMMARY")
    print("=" * 60)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    print("=" * 60)

    if orchestrator.has_execution_errors or orchestrator.has_failures:
        exit_code = 1
    else:
        exit_code = 0

    # ── Launch dashboard ──────────────────────────────────────
    if not args.no_dashboard:
        _launch_dashboard(logger)

    return exit_code


def _launch_dashboard(logger: logging.Logger) -> None:
    """Launch the Streamlit dashboard in a subprocess."""
    logger.info("─" * 50)
    logger.info("[Dashboard] Lancement du dashboard RedTeaming Framework...")
    logger.info("[Dashboard] Local   : http://localhost:8501")
    logger.info("─" * 50)
    try:
        subprocess.run(
            [
                sys.executable, "-m", "streamlit", "run", str(DASHBOARD_PATH),
                "--server.headless", "true",
                "--global.showWarningOnDirectExecution", "false",
                "--runner.magicEnabled", "false",
            ],
            check=False,
            env={**os.environ, "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false"},
        )
    except KeyboardInterrupt:
        logger.info("[Dashboard] Dashboard arrêté par l'utilisateur")
    except FileNotFoundError:
        logger.error(
            "[Dashboard] Streamlit n'est pas installé. "
            "Installez-le avec : pip install streamlit"
        )


if __name__ == "__main__":
    sys.exit(main())
