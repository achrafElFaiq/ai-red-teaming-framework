import os
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class PyritSettings:
    attacker_endpoint: str
    attacker_model: str
    attacker_api_key: str
    scorer_endpoint: str
    scorer_model: str
    scorer_api_key: str
    loop_shutdown_delay: float
    dataset_max_concurrency: int


def load_pyrit_settings() -> PyritSettings:
    return PyritSettings(
        attacker_endpoint=os.getenv("PYRIT_ATTACKER_ENDPOINT", ""),
        attacker_model=os.getenv("PYRIT_ATTACKER_MODEL", ""),
        attacker_api_key=os.getenv("PYRIT_ATTACKER_API_KEY", ""),
        scorer_endpoint=os.getenv("PYRIT_SCORER_ENDPOINT", ""),
        scorer_model=os.getenv("PYRIT_SCORER_MODEL", ""),
        scorer_api_key=os.getenv("PYRIT_SCORER_API_KEY", ""),
        loop_shutdown_delay=float(os.getenv("PYRIT_LOOP_SHUTDOWN_DELAY", "0.3")),
        dataset_max_concurrency=int(os.getenv("PYRIT_DATASET_MAX_CONCURRENCY", "5")),
    )


def _resolve_api_key(key_env: str, command_env: str) -> str:
    """Resolve an API key from environment or by running a shell command.

    If ``command_env`` is set, the command is executed and its stdout is
    used as the key. Otherwise the static ``key_env`` value is returned.
    This allows enterprise setups to refresh JWT tokens dynamically.
    """
    command = os.getenv(command_env)
    if command:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise ValueError(f"{command_env} failed: {result.stderr.strip()}")
        return result.stdout.strip()
    return os.getenv(key_env, "")


def build_attacker_config(settings: PyritSettings) -> dict[str, str]:
    return {
        "attacker_endpoint": settings.attacker_endpoint,
        "attacker_model": settings.attacker_model,
        "attacker_api_key": _resolve_api_key(
            "PYRIT_ATTACKER_API_KEY", "PYRIT_ATTACKER_API_KEY_COMMAND"
        ),
    }


def build_scorer_config(settings: PyritSettings) -> dict[str, str]:
    return {
        "scorer_endpoint": settings.scorer_endpoint,
        "scorer_model": settings.scorer_model,
        "scorer_api_key": _resolve_api_key(
            "PYRIT_SCORER_API_KEY", "PYRIT_SCORER_API_KEY_COMMAND"
        ),
    }



