from __future__ import annotations

import argparse

from redteaming.application.campaign_loader import load_campaign
from redteaming.cli.common import configure_logging, get_cli_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="redteaming validate",
        description="Validate that a campaign YAML and its referenced attack files load correctly.",
    )
    parser.add_argument(
        "campaign",
        help="Path to the campaign YAML file to validate.",
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
        logger.error("[Validate] Invalid campaign: %s", exc)
        return 1

    logger.info(
        "[Validate] OK — campaign '%s' loaded with %d attack(s)",
        config.campaign_name or args.campaign,
        len(config.active_attacks),
    )
    return 0

