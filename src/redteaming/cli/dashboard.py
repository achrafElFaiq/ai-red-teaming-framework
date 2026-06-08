from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from redteaming.cli.log import configure_logging, get_cli_logger

DASHBOARD_PATH = Path(__file__).resolve().parents[1] / "ui" / "streamlit_dashboard.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="redteaming dashboard",
        description="Launch the RedTeaming Streamlit dashboard.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    return parser


def launch_dashboard(logger) -> None:
    """Launch the Streamlit dashboard in a subprocess."""
    logger.info("─" * 50)
    logger.info("[Dashboard] Launching RedTeaming Framework dashboard...")
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
        logger.info("[Dashboard] Dashboard stopped by user")
    except FileNotFoundError:
        logger.error(
            "[Dashboard] Streamlit is not installed. "
            "Install it with: pip install streamlit"
        )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.log_level)
    launch_dashboard(get_cli_logger())
    return 0


