"""Top-level CLI router with explicit subcommands only."""

from __future__ import annotations

import argparse
import sys

from redteaming.cli.dashboard import main as dashboard_main
from redteaming.cli.doctor import main as doctor_main
from redteaming.cli.run import main as run_main
from redteaming.cli.validate import main as validate_main

_SUBCOMMAND_HANDLERS = {
    "run": run_main,
    "validate": validate_main,
    "dashboard": dashboard_main,
    "doctor": doctor_main,
}

_SUBCOMMAND_HELP = {
    "run": "Execute a red teaming campaign.",
    "validate": "Validate a campaign YAML and referenced attack files.",
    "dashboard": "Launch the Streamlit dashboard.",
    "doctor": "Run preflight diagnostics for a campaign.",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="redteaming",
        description="RedTeaming Framework command-line interface.",
    )
    subparsers = parser.add_subparsers(dest="command")
    for command_name, help_text in _SUBCOMMAND_HELP.items():
        subparsers.add_parser(command_name, help=help_text)
    return parser


def _dispatch_subcommand(command: str, argv: list[str]) -> int:
    if command == "run":
        return run_main(argv, prog="redteaming run")
    return _SUBCOMMAND_HANDLERS[command](argv)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    if not args:
        parser.print_help()
        return 2

    if args[0] in {"-h", "--help"}:
        parser.print_help()
        return 0

    if args[0] in _SUBCOMMAND_HANDLERS:
        return _dispatch_subcommand(args[0], args[1:])

    available = ", ".join(sorted(_SUBCOMMAND_HANDLERS))
    print(f"usage: redteaming [-h] {{run,validate,dashboard,doctor}} ...", file=sys.stderr)
    print(
        f"redteaming: error: argument command: invalid choice: '{args[0]}' (choose from {available})",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())





