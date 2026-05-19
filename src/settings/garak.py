import os
from dataclasses import dataclass
from pathlib import Path


_DEFAULT_GARAK_REPORTS_DIR = Path.home() / ".local" / "share" / "garak" / "garak_runs" / "reports"
_DEFAULT_GARAK_CONFIG_PATH = Path(".runtime") / "garak" / "garak_config.json"


@dataclass(frozen=True)
class GarakSettings:
    garak_reports_dir: str
    garak_config_path: str
    garak_request_timeout: int
    garak_default_report_prefix: str


def load_garak_settings() -> GarakSettings:
    return GarakSettings(
        garak_reports_dir=str(_DEFAULT_GARAK_REPORTS_DIR),
        garak_config_path=str(_DEFAULT_GARAK_CONFIG_PATH),
        garak_request_timeout=int(os.getenv("GARAK_REQUEST_TIMEOUT", "60")),
        garak_default_report_prefix=os.getenv("GARAK_DEFAULT_REPORT_PREFIX", "reports/run"),
    )


