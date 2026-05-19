import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from redteaming.domain.models.attack_result import AttackResult
from redteaming.infrastructure.persistence.json_report_store import JsonReportStore


class JsonReportStoreTests(unittest.TestCase):
    def test_store_uses_runtime_reports_dir_by_default(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch(
                    "redteaming.infrastructure.persistence.json_report_store.get_runtime_settings",
                return_value=SimpleNamespace(json_reports_dir=tmp_dir),
            ):
                store = JsonReportStore()

            self.assertEqual(store.reports_dir, Path(tmp_dir))

    def test_save_batch_writes_json_reports(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = JsonReportStore(tmp_dir)
            fixed_time = datetime(2026, 4, 27, 12, 30, 45)

            results = [
                AttackResult(
                    framework="pyrit",
                    attack_name="Crescendo Attack",
                    target_url="http://localhost:8000/api/chat",
                    timestamp=fixed_time,
                ),
                AttackResult(
                    framework="garak",
                    attack_name="Dataset / Prompt 01",
                    target_url="http://localhost:8000/api/chat",
                    timestamp=fixed_time,
                ),
            ]

            paths = store.save_batch(results)

            self.assertEqual(len(paths), 2)
            self.assertTrue(all(path.exists() for path in paths))
            self.assertEqual(paths[0].name, "pyrit_crescendo_attack_20260427_123045_00.json")
            self.assertEqual(paths[1].name, "garak_dataset_prompt_01_20260427_123045_01.json")

            first_payload = json.loads(paths[0].read_text(encoding="utf-8"))
            second_payload = json.loads(paths[1].read_text(encoding="utf-8"))
            self.assertEqual(first_payload["framework"], "pyrit")
            self.assertEqual(second_payload["framework"], "garak")

    def test_save_batch_prefixes_filenames_with_campaign_run_id_when_present(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = JsonReportStore(tmp_dir)
            result = AttackResult(
                framework="pyrit",
                attack_name="Dataset Attack",
                target_url="http://localhost:8000/api/chat",
                campaign_run_id="20260505_113000_123456",
                timestamp=datetime(2026, 5, 5, 11, 30, 0),
            )

            paths = store.save_batch([result])

            self.assertEqual(len(paths), 1)
            self.assertEqual(
                paths[0].name,
                "20260505_113000_123456_pyrit_dataset_attack_20260505_113000.json",
            )

    def test_delete_files_removes_existing_report_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = JsonReportStore(tmp_dir)
            first = Path(tmp_dir) / "a.json"
            second = Path(tmp_dir) / "b.json"
            third = Path(tmp_dir) / "missing.json"
            first.write_text("{}", encoding="utf-8")
            second.write_text("{}", encoding="utf-8")

            deleted = store.delete_files([first.name, second.name, third.name])

            self.assertEqual(deleted, 2)
            self.assertFalse(first.exists())
            self.assertFalse(second.exists())


if __name__ == "__main__":
    unittest.main()

