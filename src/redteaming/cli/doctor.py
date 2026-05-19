from __future__ import annotations

import argparse

from redteaming.application.campaign_loader import load_campaign
from redteaming.application.health_check import run_preflight_checks
from redteaming.cli.common import configure_logging, get_cli_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="redteaming doctor",
        description="Run preflight diagnostics for a campaign without executing attacks.",
    )
    parser.add_argument(
        "campaign",
        help="Path to the campaign YAML file to diagnose.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.log_level)
    logger = get_cli_logger()

    try:
        config = load_campaign(args.campaign)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("[Doctor] Invalid campaign: %s", exc)
        return 1

    issues = run_preflight_checks(config)
    if issues:
        logger.error("[Doctor] ❌ %d issue(s) found", len(issues))
        for issue in issues:
            logger.error("[Doctor]   ✗ %s", issue)
        return 1

    logger.info("[Doctor] ✅ All preflight checks passed")
    return 0

