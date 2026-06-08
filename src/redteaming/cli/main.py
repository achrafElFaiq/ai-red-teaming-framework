"""CLI entry point — two commands: run and dashboard."""

from __future__ import annotations

import sys

from redteaming.cli.run import main as run_main
from redteaming.cli.dashboard import main as dashboard_main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args[0] in {"-h", "--help"}:
        print("usage: redteaming <command> [options]\n")
        print("commands:")
        print("  run <campaign.yaml>   Execute a red teaming campaign")
        print("  dashboard             Launch the Streamlit results dashboard")
        print("\nRun 'redteaming <command> --help' for details.")
        return 0 if args and args[0] in {"-h", "--help"} else 2

    command, rest = args[0], args[1:]

    if command == "run":
        return run_main(rest, prog="redteaming run")
    if command == "dashboard":
        return dashboard_main(rest)

    print(f"redteaming: unknown command '{command}' (use 'run' or 'dashboard')", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
