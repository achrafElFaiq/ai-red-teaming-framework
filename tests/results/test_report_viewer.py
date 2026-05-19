import tempfile
import unittest
from pathlib import Path

from redteaming.ui import streamlit_dashboard as report_viewer
from redteaming.ui import streamlit_dashboard


class ReportViewerHelpersTests(unittest.TestCase):
    def test_streamlit_dashboard_ui_module_keeps_legacy_helpers_accessible(self):
        self.assertIs(report_viewer.group_by_campaign, streamlit_dashboard.group_by_campaign)
        self.assertIs(report_viewer.delete_campaign_reports, streamlit_dashboard.delete_campaign_reports)

    def test_group_by_campaign_keeps_same_title_runs_separate_when_run_id_differs(self):
        reports = [
            {
                "campaign_name": "R3 — Jailbreaking",
                "campaign_run_id": "20260505_110000_000001",
                "campaign_run_timestamp": "2026-05-05T11:00:00",
                "timestamp": "2026-05-05T11:00:10",
            },
            {
                "campaign_name": "R3 — Jailbreaking",
                "campaign_run_id": "20260505_120000_000001",
                "campaign_run_timestamp": "2026-05-05T12:00:00",
                "timestamp": "2026-05-05T12:00:10",
            },
        ]

        grouped = report_viewer.group_by_campaign(reports)

        self.assertEqual(len(grouped), 2)
        self.assertIn("run:20260505_110000_000001", grouped)
        self.assertIn("run:20260505_120000_000001", grouped)

    def test_campaign_label_includes_human_title_and_run_timestamp(self):
        reports = [
            {
                "campaign_name": "R1 — System Prompt Leakage",
                "campaign_run_id": "20260505_110000_000001",
                "campaign_run_timestamp": "2026-05-05T11:00:00",
            }
        ]

        label = report_viewer.campaign_label(reports)

        self.assertEqual(label, "R1 — System Prompt Leakage · 2026-05-05 11:00:00")

    def test_delete_campaign_reports_removes_only_selected_report_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            reports_path = Path(tmp_dir)
            keep = reports_path / "keep.json"
            delete_a = reports_path / "delete-a.json"
            delete_b = reports_path / "delete-b.json"
            keep.write_text("{}", encoding="utf-8")
            delete_a.write_text("{}", encoding="utf-8")
            delete_b.write_text("{}", encoding="utf-8")

            deleted = report_viewer.delete_campaign_reports(
                reports_path,
                [{"_filename": delete_a.name}, {"_filename": delete_b.name}],
            )

            self.assertEqual(deleted, 2)
            self.assertTrue(keep.exists())
            self.assertFalse(delete_a.exists())
            self.assertFalse(delete_b.exists())


if __name__ == "__main__":
    unittest.main()


