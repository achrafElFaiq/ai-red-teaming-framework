from pathlib import Path
from types import SimpleNamespace

import os

from dotenv import load_dotenv

_env_loaded = False


def ensure_env_loaded() -> None:
    """Load the root .env file once."""
    global _env_loaded
    if not _env_loaded:
        load_dotenv(Path(__file__).resolve().parents[3] / ".env")
        _env_loaded = True


from .garak import GarakSettings
from .garak import load_garak_settings
from .pyrit import PyritSettings, build_attacker_config, build_scorer_config, load_pyrit_settings
from .reports import ReportsSettings
from .reports import load_reports_settings


def get_runtime_settings(frameworks: set[str] | None = None) -> SimpleNamespace:
    """Read runtime settings from environment variables.

    Returns a SimpleNamespace with .reports, .pyrit, .garak attributes.
    """
    ensure_env_loaded()

    need_pyrit = frameworks is None or "pyrit" in frameworks

    reports = load_reports_settings()
    pyrit = load_pyrit_settings()
    garak = load_garak_settings()

    if need_pyrit:
        if not pyrit.attacker_endpoint:
            raise ValueError("Missing required environment variable: PYRIT_ATTACKER_ENDPOINT")
        if not pyrit.attacker_model:
            raise ValueError("Missing required environment variable: PYRIT_ATTACKER_MODEL")
        if not pyrit.attacker_api_key and not os.getenv("PYRIT_ATTACKER_API_KEY_COMMAND"):
            raise ValueError(
                "Missing required environment variable: PYRIT_ATTACKER_API_KEY or PYRIT_ATTACKER_API_KEY_COMMAND")
        if not pyrit.scorer_endpoint:
            raise ValueError("Missing required environment variable: PYRIT_SCORER_ENDPOINT")
        if not pyrit.scorer_model:
            raise ValueError("Missing required environment variable: PYRIT_SCORER_MODEL")
        if not pyrit.scorer_api_key and not os.getenv("PYRIT_SCORER_API_KEY_COMMAND"):
            raise ValueError(
                "Missing required environment variable: PYRIT_SCORER_API_KEY or PYRIT_SCORER_API_KEY_COMMAND")

    return SimpleNamespace(reports=reports, pyrit=pyrit, garak=garak)


def get_reports_settings() -> ReportsSettings:
    return load_reports_settings()


def get_pyrit_settings() -> PyritSettings:
    ensure_env_loaded()
    return load_pyrit_settings()


def get_garak_settings() -> GarakSettings:
    ensure_env_loaded()
    return load_garak_settings()


def build_pyrit_attacker_config() -> dict[str, str]:
    return build_attacker_config(get_pyrit_settings())


def build_pyrit_scorer_config() -> dict[str, str]:
    return build_scorer_config(get_pyrit_settings())

__all__ = [
    "ReportsSettings",
    "PyritSettings",
    "GarakSettings",
    "ensure_env_loaded",
    "get_runtime_settings",
    "get_reports_settings",
    "get_pyrit_settings",
    "get_garak_settings",
    "build_pyrit_attacker_config",
    "build_pyrit_scorer_config",
]
