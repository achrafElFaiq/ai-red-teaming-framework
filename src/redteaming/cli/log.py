from __future__ import annotations

import logging


class ScorerRetryFilter(logging.Filter):
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


def configure_logging(level: str) -> None:
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

    scorer_logger = logging.getLogger("pyrit.exceptions.exceptions_helpers")
    if not any(isinstance(existing_filter, ScorerRetryFilter) for existing_filter in scorer_logger.filters):
        scorer_logger.addFilter(ScorerRetryFilter())


def get_cli_logger() -> logging.Logger:
    return logging.getLogger("RedTeaming Framework")

