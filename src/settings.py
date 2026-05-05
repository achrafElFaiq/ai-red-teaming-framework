import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_env_loaded = False


def ensure_env_loaded() -> None:
	"""Load the root .env file once."""
	global _env_loaded
	if not _env_loaded:
		load_dotenv(Path(__file__).resolve().parent.parent / ".env")
		_env_loaded = True


@dataclass(frozen=True)
class RuntimeSettings:
	pyrit_attacker_endpoint: str
	pyrit_attacker_model: str
	pyrit_attacker_api_key: str
	pyrit_scorer_endpoint: str
	pyrit_scorer_model: str
	pyrit_scorer_api_key: str
	pyrit_db_path: str
	pyrit_loop_shutdown_delay: float
	pyrit_dataset_max_concurrency: int
	default_target_url: str
	json_reports_dir: str
	garak_reports_dir: str
	garak_config_path: str
	garak_request_timeout: int
	garak_default_report_prefix: str


def get_runtime_settings(frameworks: set[str] | None = None) -> RuntimeSettings:
	"""Read runtime settings from environment variables."""
	ensure_env_loaded()

	need_pyrit = frameworks is None or "pyrit" in frameworks
	need_garak = frameworks is None or "garak" in frameworks

	settings = RuntimeSettings(
		# PyRIT
		pyrit_attacker_endpoint=os.getenv("PYRIT_ATTACKER_ENDPOINT", ""),
		pyrit_attacker_model=os.getenv("PYRIT_ATTACKER_MODEL", ""),
		pyrit_attacker_api_key=os.getenv("PYRIT_ATTACKER_API_KEY", ""),
		pyrit_scorer_endpoint=os.getenv("PYRIT_SCORER_ENDPOINT", ""),
		pyrit_scorer_model=os.getenv("PYRIT_SCORER_MODEL", ""),
		pyrit_scorer_api_key=os.getenv("PYRIT_SCORER_API_KEY", ""),
		pyrit_db_path=os.getenv("PYRIT_DB_PATH", ""),
		pyrit_loop_shutdown_delay=float(os.getenv("PYRIT_LOOP_SHUTDOWN_DELAY", "0.3")),
		pyrit_dataset_max_concurrency=int(os.getenv("PYRIT_DATASET_MAX_CONCURRENCY", "5")),

		# Always required
		default_target_url=os.getenv("DEFAULT_TARGET_URL", ""),
		json_reports_dir=os.getenv("JSON_REPORTS_DIR", ""),

		# Garak
		garak_reports_dir=os.getenv("GARAK_REPORTS_DIR", ""),
		garak_config_path=os.getenv("GARAK_CONFIG_PATH", ""),
		garak_request_timeout=int(os.getenv("GARAK_REQUEST_TIMEOUT", "60")),
		garak_default_report_prefix=os.getenv("GARAK_DEFAULT_REPORT_PREFIX", "reports/run"),
	)

	if not settings.default_target_url:
		raise ValueError("Missing required environment variable: DEFAULT_TARGET_URL")
	if not settings.json_reports_dir:
		raise ValueError("Missing required environment variable: JSON_REPORTS_DIR")

	if need_pyrit:
		if not settings.pyrit_attacker_endpoint:
			raise ValueError("Missing required environment variable: PYRIT_ATTACKER_ENDPOINT")
		if not settings.pyrit_attacker_model:
			raise ValueError("Missing required environment variable: PYRIT_ATTACKER_MODEL")
		if not settings.pyrit_attacker_api_key:
			raise ValueError("Missing required environment variable: PYRIT_ATTACKER_API_KEY")
		if not settings.pyrit_scorer_endpoint:
			raise ValueError("Missing required environment variable: PYRIT_SCORER_ENDPOINT")
		if not settings.pyrit_scorer_model:
			raise ValueError("Missing required environment variable: PYRIT_SCORER_MODEL")
		if not settings.pyrit_scorer_api_key:
			raise ValueError("Missing required environment variable: PYRIT_SCORER_API_KEY")
		if not settings.pyrit_db_path:
			raise ValueError("Missing required environment variable: PYRIT_DB_PATH")

	if need_garak:
		if not settings.garak_reports_dir:
			raise ValueError("Missing required environment variable: GARAK_REPORTS_DIR")
		if not settings.garak_config_path:
			raise ValueError("Missing required environment variable: GARAK_CONFIG_PATH")

	return settings


# ─────────────────────────────────────────────────────────────────
# PyRIT config helpers (called lazily by runners)
# ─────────────────────────────────────────────────────────────────

def build_pyrit_attacker_config() -> dict[str, str]:
	settings = get_runtime_settings(frameworks={"pyrit"})
	return {
		"attacker_endpoint": settings.pyrit_attacker_endpoint,
		"attacker_model": settings.pyrit_attacker_model,
		"attacker_api_key": settings.pyrit_attacker_api_key,
	}


def build_pyrit_scorer_config() -> dict[str, str]:
	settings = get_runtime_settings(frameworks={"pyrit"})
	return {
		"scorer_endpoint": settings.pyrit_scorer_endpoint,
		"scorer_model": settings.pyrit_scorer_model,
		"scorer_api_key": settings.pyrit_scorer_api_key,
	}


__all__ = [
	"RuntimeSettings",
	"ensure_env_loaded",
	"get_runtime_settings",
	"build_pyrit_attacker_config",
	"build_pyrit_scorer_config",
]
