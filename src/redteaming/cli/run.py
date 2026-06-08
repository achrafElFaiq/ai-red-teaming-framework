from __future__ import annotations

import argparse
import json

from redteaming.application.campaign_loader import load_campaign
from redteaming.application.health_check import run_preflight_checks
from redteaming.application.orchestrator import AttackOrchestrator
from redteaming.cli.log import configure_logging, get_cli_logger
from redteaming.cli.dashboard import launch_dashboard
from redteaming.infrastructure.http_attack_target import AttackTarget


def build_parser(prog: str = "RedTeaming Framework") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
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
    return parser


def execute(args: argparse.Namespace) -> int:
    logger = get_cli_logger()

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

    target = AttackTarget(
        name=config.target_name,
        chat_url=config.target_chat_url,
        reset_memory_url=config.target_reset_memory_url or None,
        input_field=config.target_input_field,
        output_field=config.target_output_field,
        model=config.target_model,
        architecture_type=config.target_architecture_type,
    )
    orchestrator = AttackOrchestrator(
        target=target,
        campaign_name=config.campaign_name,
    )
    for attack in config.active_attacks:
        orchestrator.add_attack(attack)

    orchestrator.execute_attacks()

    summary = orchestrator.summary()
    print("\n" + "=" * 60)
    print("  CAMPAIGN SUMMARY")
    print("=" * 60)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    print("=" * 60)

    exit_code = 1 if (orchestrator.has_execution_errors or orchestrator.has_failures) else 0

    if not args.no_dashboard:
        launch_dashboard(logger)

    return exit_code


def main(argv: list[str] | None = None, *, prog: str = "RedTeaming Framework") -> int:
    parser = build_parser(prog=prog)
    args = parser.parse_args(argv)
    configure_logging(args.log_level)
    return execute(args)

