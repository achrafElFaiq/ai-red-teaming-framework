from dataclasses import dataclass

from .garak import GarakSettings
from .pyrit import PyritSettings
from .reports import ReportsSettings


@dataclass(frozen=True)
class RuntimeSettings:
    reports: ReportsSettings
    pyrit: PyritSettings
    garak: GarakSettings

    @property
    def json_reports_dir(self) -> str:
        return self.reports.json_reports_dir

    @property
    def pyrit_attacker_endpoint(self) -> str:
        return self.pyrit.attacker_endpoint

    @property
    def pyrit_attacker_model(self) -> str:
        return self.pyrit.attacker_model

    @property
    def pyrit_attacker_api_key(self) -> str:
        return self.pyrit.attacker_api_key

    @property
    def pyrit_scorer_endpoint(self) -> str:
        return self.pyrit.scorer_endpoint

    @property
    def pyrit_scorer_model(self) -> str:
        return self.pyrit.scorer_model

    @property
    def pyrit_scorer_api_key(self) -> str:
        return self.pyrit.scorer_api_key

    @property
    def pyrit_loop_shutdown_delay(self) -> float:
        return self.pyrit.loop_shutdown_delay

    @property
    def pyrit_dataset_max_concurrency(self) -> int:
        return self.pyrit.dataset_max_concurrency

    @property
    def garak_reports_dir(self) -> str:
        return self.garak.garak_reports_dir

    @property
    def garak_config_path(self) -> str:
        return self.garak.garak_config_path

    @property
    def garak_request_timeout(self) -> int:
        return self.garak.garak_request_timeout

    @property
    def garak_default_report_prefix(self) -> str:
        return self.garak.garak_default_report_prefix



