"""
Pre-flight health checks for campaign components.

Verifies connectivity and availability of all components *actually needed*
by the attacks in a campaign before any expensive LLM calls begin.

Usage::

    from core.application.health_check import run_preflight_checks

    issues = run_preflight_checks(config)
    if issues:
        for issue in issues:
            logger.error(issue)
        sys.exit(1)
"""

import logging
import os
from pathlib import Path

import requests

from core.application.campaign_config import CampaignConfig

logger = logging.getLogger(__name__)


def run_preflight_checks(config: CampaignConfig) -> list[str]:
    """Run all relevant health checks and return a list of issues (empty = all OK).

    Checks are conditional on which frameworks the campaign actually uses:
    - PyRIT campaigns  → attacker LLM, scorer LLM, database file
    - Garak campaigns  → (no external LLM needed, garak handles it)
    - Always           → target endpoint reachability
    """
    issues: list[str] = []
    frameworks = _detect_frameworks(config)

    logger.info("[Preflight] Checking components for frameworks: %s", ", ".join(sorted(frameworks)))

    # ── Target health check (always) ──────────────────────────
    issues.extend(
        _check_target(
            config.target_chat_url,
            config.target_input_field,
        )
    )

    # ── PyRIT-specific checks ─────────────────────────────────
    if "pyrit" in frameworks:
        from settings import get_runtime_settings
        settings = get_runtime_settings(frameworks={"pyrit"})
        issues.extend(_check_llm_endpoint("Attacker LLM", settings.pyrit_attacker_endpoint, settings.pyrit_attacker_api_key))
        issues.extend(_check_llm_endpoint("Scorer LLM", settings.pyrit_scorer_endpoint, settings.pyrit_scorer_api_key))
        issues.extend(_check_pyrit_db(settings.pyrit_db_path))

    # ── Garak-specific checks ─────────────────────────────────
    if "garak" in frameworks:
        issues.extend(_check_garak_available())

    if not issues:
        logger.info("[Preflight] ✅ All checks passed")
    else:
        logger.error("[Preflight] ❌ %d issue(s) found", len(issues))

    return issues


def _detect_frameworks(config: CampaignConfig) -> set[str]:
    """Detect which frameworks are used in the campaign."""
    return {attack.framework for attack in config.active_attacks}


# ─────────────────────────────────────────────────────────────────
# Target check
# ─────────────────────────────────────────────────────────────────

def _check_target(target_url: str, input_field: str) -> list[str]:
    """Verify the target endpoint is reachable."""
    logger.info("[Preflight] Checking target: %s", target_url)
    payload = {input_field: "health check"}

    try:
        resp = requests.post(
            target_url,
            json=payload,
            timeout=(5, 10),
        )
        if resp.status_code < 500:
            logger.info("[Preflight] ✅ Target reachable (HTTP %d)", resp.status_code)
            return []
        return [f"Target {target_url} returned server error HTTP {resp.status_code}"]
    except requests.ConnectionError:
        return [f"Target {target_url} is not reachable (connection refused)"]
    except requests.Timeout:
        return [f"Target {target_url} timed out"]
    except requests.RequestException as exc:
        return [f"Target {target_url} check failed: {exc}"]


# ─────────────────────────────────────────────────────────────────
# LLM endpoint check (PyRIT attacker / scorer)
# ─────────────────────────────────────────────────────────────────

def _check_llm_endpoint(name: str, endpoint: str, api_key: str) -> list[str]:
    """Ping an OpenAI-compatible LLM endpoint via /models."""
    logger.info("[Preflight] Checking %s: %s", name, endpoint)
    # Try the /models endpoint (standard OpenAI-compatible discovery)
    models_url = endpoint.rstrip("/")
    if models_url.endswith("/v1"):
        models_url += "/models"
    elif not models_url.endswith("/models"):
        models_url += "/models"

    headers = {}
    if api_key and api_key not in ("ollama", "none", ""):
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.get(models_url, headers=headers, timeout=(5, 10))
        if resp.status_code < 500:
            logger.info("[Preflight] ✅ %s reachable (HTTP %d)", name, resp.status_code)
            return []
        return [f"{name} at {endpoint} returned server error HTTP {resp.status_code}"]
    except requests.ConnectionError:
        return [f"{name} at {endpoint} is not reachable (connection refused). Is the LLM server running?"]
    except requests.Timeout:
        return [f"{name} at {endpoint} timed out"]
    except requests.RequestException as exc:
        return [f"{name} at {endpoint} check failed: {exc}"]


# ─────────────────────────────────────────────────────────────────
# PyRIT database check
# ─────────────────────────────────────────────────────────────────

def _check_pyrit_db(db_path: str) -> list[str]:
    """Verify the PyRIT database directory is writable."""
    logger.info("[Preflight] Checking PyRIT DB path: %s", db_path)
    db_dir = Path(db_path).parent
    if not db_dir.exists():
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info("[Preflight] ✅ Created DB directory: %s", db_dir)
            return []
        except OSError as exc:
            return [f"Cannot create PyRIT DB directory {db_dir}: {exc}"]

    if not os.access(str(db_dir), os.W_OK):
        return [f"PyRIT DB directory {db_dir} is not writable"]

    logger.info("[Preflight] ✅ PyRIT DB directory exists and is writable")
    return []


# ─────────────────────────────────────────────────────────────────
# Garak availability check
# ─────────────────────────────────────────────────────────────────

def _check_garak_available() -> list[str]:
    """Check that garak is importable / installed."""
    logger.info("[Preflight] Checking Garak availability")
    import subprocess
    result = subprocess.run(
        ["python3", "-m", "garak", "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode == 0:
        logger.info("[Preflight] ✅ Garak is installed and available")
        return []
    return ["Garak is not installed or not available. Install with: pip install garak"]



