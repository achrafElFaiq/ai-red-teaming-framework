from dataclasses import dataclass


@dataclass(frozen=True)
class ReportsSettings:
    json_reports_dir: str


def load_reports_settings() -> ReportsSettings:
    return ReportsSettings(
        json_reports_dir="reports",
    )


