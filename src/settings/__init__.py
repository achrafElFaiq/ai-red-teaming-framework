from pathlib import Path

import os

from dotenv import load_dotenv

_env_loaded = False


def ensure_env_loaded() -> None:
    """Load the root .env file once."""
    global _env_loaded
    if not _env_loaded:
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
        _env_loaded = True


from .garak import GarakSettings
from .garak import load_garak_settings
from .pyrit import PyritSettings, build_attacker_config, build_scorer_config, load_pyrit_settings
from .reports import ReportsSettings
from .reports import load_reports_settings
from .runtime import RuntimeSettings


def get_runtime_settings(frameworks: set[str] | None = None) -> RuntimeSettings:
    """Read runtime settings from environment variables."""
    ensure_env_loaded()

    need_pyrit = frameworks is None or "pyrit" in frameworks
    need_garak = frameworks is None or "garak" in frameworks

    settings = RuntimeSettings(
        reports=load_reports_settings(),
        pyrit=load_pyrit_settings(),
        garak=load_garak_settings(),
    )

    if need_pyrit:
        if not settings.pyrit.attacker_endpoint:
            raise ValueError("Missing required environment variable: PYRIT_ATTACKER_ENDPOINT")
        if not settings.pyrit.attacker_model:
            raise ValueError("Missing required environment variable: PYRIT_ATTACKER_MODEL")
        if not settings.pyrit.attacker_api_key and not os.getenv("PYRIT_ATTACKER_API_KEY_COMMAND"):
            raise ValueError(
                "Missing required environment variable: PYRIT_ATTACKER_API_KEY or PYRIT_ATTACKER_API_KEY_COMMAND")
        if not settings.pyrit.scorer_endpoint:
            raise ValueError("Missing required environment variable: PYRIT_SCORER_ENDPOINT")
        if not settings.pyrit.scorer_model:
            raise ValueError("Missing required environment variable: PYRIT_SCORER_MODEL")
        if not settings.pyrit.scorer_api_key and not os.getenv("PYRIT_SCORER_API_KEY_COMMAND"):
            raise ValueError(
                "Missing required environment variable: PYRIT_SCORER_API_KEY or PYRIT_SCORER_API_KEY_COMMAND")

    return settings


def get_reports_settings() -> ReportsSettings:
    return get_runtime_settings(frameworks=set()).reports


def get_pyrit_settings() -> PyritSettings:
    return get_runtime_settings(frameworks={"pyrit"}).pyrit


def get_garak_settings() -> GarakSettings:
    return get_runtime_settings(frameworks={"garak"}).garak


def build_pyrit_attacker_config() -> dict[str, str]:
    return build_attacker_config(get_pyrit_settings())


def build_pyrit_scorer_config() -> dict[str, str]:
    return build_scorer_config(get_pyrit_settings())

__all__ = [
    "ReportsSettings",
    "PyritSettings",
    "GarakSettings",
    "RuntimeSettings",
    "ensure_env_loaded",
    "get_runtime_settings",
    "get_reports_settings",
    "get_pyrit_settings",
    "get_garak_settings",
    "build_pyrit_attacker_config",
    "build_pyrit_scorer_config",
]




