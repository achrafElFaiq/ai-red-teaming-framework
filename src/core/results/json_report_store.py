from datetime import datetime
import logging
from pathlib import Path

from settings import get_runtime_settings
from core.models.attack_result import AttackResult
from core.utils import slugify


logger = logging.getLogger(__name__)


class JsonReportStore:
    def __init__(self, reports_dir: str | Path | None = None):
        resolved_reports_dir = reports_dir or get_runtime_settings(frameworks=set()).json_reports_dir
        self.reports_dir = Path(resolved_reports_dir)

    def save_batch(self, results: list[AttackResult]) -> list[Path]:
        if not results:
            return []

        self.reports_dir.mkdir(parents=True, exist_ok=True)
        total = len(results)
        saved_paths: list[Path] = []

        for index, result in enumerate(results):
            saved_paths.append(self._save_result(result, index=index, total=total))

        logger.debug("Saved %d report file(s)", len(saved_paths))
        return saved_paths

    def delete_files(self, filenames: list[str]) -> int:
        deleted = 0
        for filename in filenames:
            path = self.reports_dir / Path(filename).name
            if path.exists() and path.is_file():
                path.unlink()
                deleted += 1

        logger.debug("Deleted %d report file(s)", deleted)
        return deleted

    def _save_result(self, result: AttackResult, index: int, total: int) -> Path:
        timestamp = result.timestamp
        if not isinstance(timestamp, datetime):
            timestamp = datetime.now()

        filename = f"{result.framework}_{slugify(result.attack_name)}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        if result.campaign_run_id:
            filename = f"{result.campaign_run_id}_{filename}"
        if total > 1:
            filename = f"{filename}_{index:02d}"

        path = self.reports_dir / f"{filename}.json"
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        logger.debug("Saved report for attack '%s' to %s", result.attack_name, path)
        return path

