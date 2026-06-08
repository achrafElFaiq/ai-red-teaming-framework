"""Pre-flight health checks for campaign components."""

import logging
import subprocess
import sys

import requests

from redteaming.application.campaign_config import CampaignConfig

logger = logging.getLogger(__name__)


def run_preflight_checks(config: CampaignConfig) -> list[str]:
    """Run all relevant health checks and return a list of issues (empty = all OK)."""
    issues: list[str] = []
    frameworks = _detect_frameworks(config)

    logger.info("[Preflight] Checking components for frameworks: %s", ", ".join(sorted(frameworks)))

    issues.extend(_check_target(config.target_chat_url, config.target_input_field))

    if "pyrit" in frameworks:
        from redteaming.settings import get_runtime_settings, build_pyrit_attacker_config, build_pyrit_scorer_config
        settings = get_runtime_settings(frameworks={"pyrit"})
        attacker_config = build_pyrit_attacker_config()
        scorer_config = build_pyrit_scorer_config()
        issues.extend(_check_llm_endpoint("Attacker LLM", settings.pyrit.attacker_endpoint, attacker_config["attacker_api_key"]))
        issues.extend(_check_llm_endpoint("Scorer LLM", settings.pyrit.scorer_endpoint, scorer_config["scorer_api_key"]))

    if "garak" in frameworks:
        issues.extend(_check_garak_available())

    if not issues:
        logger.info("[Preflight] ✅ All checks passed")
    else:
        logger.error("[Preflight] ❌ %d issue(s) found", len(issues))

    return issues


def _detect_frameworks(config: CampaignConfig) -> set[str]:
    return {attack.framework for attack in config.active_attacks}


def _check_target(target_url: str, input_field: str) -> list[str]:
    logger.info("[Preflight] Checking target: %s", target_url)
    payload = {input_field: "health check"}

    try:
        resp = requests.post(target_url, json=payload, timeout=(5, 10))
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


def _check_llm_endpoint(name: str, endpoint: str, api_key: str) -> list[str]:
    logger.info("[Preflight] Checking %s: %s", name, endpoint)
    models_url = endpoint.rstrip("/")
    if not models_url.endswith("/models"):
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


def _check_garak_available() -> list[str]:
    logger.info("[Preflight] Checking Garak availability")

    result = subprocess.run(
        [sys.executable, "-m", "garak", "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )

    if result.returncode == 0:
        logger.info("[Preflight] ✅ Garak is installed and available")
        return []
    return ["Garak is not installed or not available. Install with: pip install garak"]
