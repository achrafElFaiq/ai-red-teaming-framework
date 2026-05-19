"""Repository entry shim for the packaged RedTeaming CLI."""

import sys

try:
    from redteaming.cli.main import main
except ModuleNotFoundError as exc:
    if exc.name == "redteaming":
        raise SystemExit(
            "The packaged CLI is not available yet in this environment. "
            "Run `pip install -e .` from the repository root, then retry."
        ) from exc
    raise


if __name__ == "__main__":
    sys.exit(main())
