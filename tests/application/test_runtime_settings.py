import os
import unittest
from pathlib import Path
from unittest.mock import patch

import redteaming.settings as settings_module
from redteaming.settings import build_pyrit_attacker_config, get_garak_settings, get_pyrit_settings, get_reports_settings, get_runtime_settings


# PyRIT-specific env vars
_PYRIT_ENV = {
    "PYRIT_ATTACKER_ENDPOINT": "http://127.0.0.1:11434/v1",
    "PYRIT_ATTACKER_MODEL": "gemma4:e4b",
    "PYRIT_ATTACKER_API_KEY": "ollama",
    "PYRIT_SCORER_ENDPOINT": "http://127.0.0.1:11434/v1",
    "PYRIT_SCORER_MODEL": "gemma4:e4b",
    "PYRIT_SCORER_API_KEY": "ollama",
}

# Garak-specific env vars
_GARAK_ENV = {
    "GARAK_REQUEST_TIMEOUT": "60",
}

# All env vars combined
_FULL_ENV = {**_PYRIT_ENV, **_GARAK_ENV}


class RuntimeSettingsTests(unittest.TestCase):
    def setUp(self):
        settings_module._env_loaded = False
        self.load_dotenv_patcher = patch("redteaming.settings.load_dotenv", return_value=False)
        self.load_dotenv_patcher.start()

    def tearDown(self):
        self.load_dotenv_patcher.stop()
        settings_module._env_loaded = False

    def test_runtime_settings_raise_when_env_vars_are_missing(self):
        """Calling get_runtime_settings() with no env and no framework filter should crash."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Missing required environment variable"):
                get_runtime_settings()

    def test_pyrit_only_campaign_does_not_require_garak_vars(self):
        """A PyRIT-only campaign should NOT require GARAK_ vars."""
        with patch.dict(os.environ, _PYRIT_ENV, clear=True):
            settings = get_runtime_settings(frameworks={"pyrit"})
        self.assertEqual(settings.pyrit.attacker_endpoint, "http://127.0.0.1:11434/v1")
        self.assertEqual(settings.garak.garak_reports_dir, str(Path.home() / ".local" / "share" / "garak" / "garak_runs" / "reports"))
        self.assertEqual(settings.garak.garak_config_path, ".runtime/garak/garak_config.json")

    def test_garak_only_campaign_does_not_require_pyrit_vars(self):
        """A Garak-only campaign should NOT require PYRIT_ vars."""
        with patch.dict(os.environ, _GARAK_ENV, clear=True):
            settings = get_runtime_settings(frameworks={"garak"})
        self.assertEqual(settings.garak.garak_reports_dir, str(Path.home() / ".local" / "share" / "garak" / "garak_runs" / "reports"))
        self.assertEqual(settings.garak.garak_config_path, ".runtime/garak/garak_config.json")
        self.assertEqual(settings.pyrit.attacker_endpoint, "")  # empty default, not required

    def test_pyrit_only_campaign_raises_if_pyrit_vars_missing(self):
        """A PyRIT campaign should fail if PYRIT_ vars are missing."""
        with patch.dict(os.environ, _GARAK_ENV, clear=True):
            with self.assertRaisesRegex(ValueError, "PYRIT_ATTACKER_ENDPOINT"):
                get_runtime_settings(frameworks={"pyrit"})

    def test_garak_only_campaign_uses_internal_paths_when_env_vars_are_missing(self):
        """A Garak campaign should use built-in internal paths without GARAK_* env vars."""
        with patch.dict(os.environ, {}, clear=True):
            settings = get_runtime_settings(frameworks={"garak"})

        self.assertEqual(settings.garak.garak_reports_dir, str(Path.home() / ".local" / "share" / "garak" / "garak_runs" / "reports"))
        self.assertEqual(settings.garak.garak_config_path, ".runtime/garak/garak_config.json")

    def test_reports_dir_is_fixed_to_reports(self):
        """The framework always stores JSON reports in the built-in 'reports' directory."""
        with patch.dict(os.environ, _PYRIT_ENV, clear=True):
            settings = get_runtime_settings(frameworks={"pyrit"})

        self.assertEqual(settings.reports.json_reports_dir, "reports")

    def test_technical_vars_have_sensible_defaults(self):
        """PYRIT_LOOP_SHUTDOWN_DELAY, PYRIT_DATASET_MAX_CONCURRENCY, GARAK_REQUEST_TIMEOUT
        should use defaults when not explicitly set."""
        with patch.dict(os.environ, _FULL_ENV, clear=True):
            settings = get_runtime_settings()
        self.assertEqual(settings.pyrit.loop_shutdown_delay, 0.3)
        self.assertEqual(settings.pyrit.dataset_max_concurrency, 5)
        self.assertEqual(settings.garak.garak_request_timeout, 60)
        self.assertEqual(settings.garak.garak_default_report_prefix, "reports/run")

    def test_technical_vars_can_be_overridden(self):
        """Technical defaults can be overridden via env vars."""
        env = {**_FULL_ENV, "PYRIT_LOOP_SHUTDOWN_DELAY": "1.5", "GARAK_REQUEST_TIMEOUT": "90"}
        with patch.dict(os.environ, env, clear=True):
            settings = get_runtime_settings()
        self.assertEqual(settings.pyrit.loop_shutdown_delay, 1.5)
        self.assertEqual(settings.garak.garak_request_timeout, 90)

    def test_runtime_settings_load_all_values(self):
        env = {
            **_FULL_ENV,
            "PYRIT_ATTACKER_ENDPOINT": "https://llm.example.test/v1",
            "PYRIT_ATTACKER_MODEL": "gpt-test",
            "PYRIT_ATTACKER_API_KEY": "secret",
            "PYRIT_SCORER_ENDPOINT": "https://scorer.example.test/v1",
            "PYRIT_SCORER_MODEL": "scorer-model",
            "PYRIT_SCORER_API_KEY": "scorer-secret",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = get_runtime_settings()
            attacker_config = build_pyrit_attacker_config()

        self.assertEqual(settings.pyrit.attacker_endpoint, "https://llm.example.test/v1")
        self.assertEqual(settings.pyrit.attacker_model, "gpt-test")
        self.assertEqual(settings.pyrit.attacker_api_key, "secret")
        self.assertEqual(settings.pyrit.scorer_endpoint, "https://scorer.example.test/v1")
        self.assertEqual(settings.pyrit.scorer_model, "scorer-model")
        self.assertEqual(settings.pyrit.scorer_api_key, "scorer-secret")
        self.assertEqual(settings.reports.json_reports_dir, "reports")
        self.assertEqual(settings.garak.garak_reports_dir, str(Path.home() / ".local" / "share" / "garak" / "garak_runs" / "reports"))
        self.assertEqual(settings.garak.garak_config_path, ".runtime/garak/garak_config.json")
        self.assertEqual(
            attacker_config,
            {
                "attacker_endpoint": "https://llm.example.test/v1",
                "attacker_model": "gpt-test",
                "attacker_api_key": "secret",
            },
        )

    def test_specialized_settings_classes_are_loaded_cleanly(self):
        with patch.dict(os.environ, _FULL_ENV, clear=True):
            reports = get_reports_settings()
            pyrit = get_pyrit_settings()
            garak = get_garak_settings()

        self.assertEqual(reports.json_reports_dir, "reports")
        self.assertEqual(pyrit.attacker_endpoint, "http://127.0.0.1:11434/v1")
        self.assertEqual(pyrit.scorer_model, "gemma4:e4b")
        self.assertEqual(garak.garak_reports_dir, str(Path.home() / ".local" / "share" / "garak" / "garak_runs" / "reports"))
        self.assertEqual(garak.garak_config_path, ".runtime/garak/garak_config.json")


if __name__ == "__main__":
    unittest.main()

