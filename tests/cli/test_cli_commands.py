from types import SimpleNamespace
from unittest.mock import patch

from redteaming.cli import dashboard as dashboard_cli
from redteaming.cli import doctor as doctor_cli
from redteaming.cli import main as cli_main
from redteaming.cli import validate as validate_cli


def test_main_dispatches_run_subcommand_explicitly():
    with patch("redteaming.cli.main.run_main", return_value=3) as run_main_mock:
        exit_code = cli_main.main(["run", "campaign.yaml", "--skip-checks"])

    assert exit_code == 3
    run_main_mock.assert_called_once_with(["campaign.yaml", "--skip-checks"], prog="redteaming run")


def test_main_dispatches_validate_subcommand():
    called = {}

    def fake_validate(argv):
        called["argv"] = argv
        return 7

    with patch.dict(cli_main._SUBCOMMAND_HANDLERS, {"validate": fake_validate}):
        exit_code = cli_main.main(["validate", "campaign.yaml"])

    assert exit_code == 7
    assert called["argv"] == ["campaign.yaml"]


def test_main_rejects_missing_subcommand(capsys):
    exit_code = cli_main.main([])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "usage: redteaming" in captured.out


def test_main_top_level_help_returns_zero(capsys):
    exit_code = cli_main.main(["--help"])

    assert exit_code == 0
    assert "usage: redteaming" in capsys.readouterr().out


def test_main_rejects_unknown_command(capsys):
    exit_code = cli_main.main(["campaign.yaml"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "invalid choice" in captured.err


def test_validate_returns_success_when_campaign_loads():
    with patch("redteaming.cli.validate.configure_logging"), patch(
        "redteaming.cli.validate.load_campaign",
        return_value=SimpleNamespace(campaign_name="Smoke", active_attacks=[object(), object()]),
    ):
        exit_code = validate_cli.main(["campaign.yaml"])

    assert exit_code == 0


def test_doctor_returns_failure_when_preflight_finds_issues():
    with patch("redteaming.cli.doctor.configure_logging"), patch(
        "redteaming.cli.doctor.load_campaign",
        return_value=SimpleNamespace(campaign_name="Smoke", active_attacks=[]),
    ), patch("redteaming.cli.doctor.run_preflight_checks", return_value=["target down"]):
        exit_code = doctor_cli.main(["campaign.yaml"])

    assert exit_code == 1


def test_dashboard_main_launches_dashboard_and_returns_zero():
    with patch("redteaming.cli.dashboard.configure_logging"), patch(
        "redteaming.cli.dashboard.launch_dashboard"
    ) as launch_mock:
        exit_code = dashboard_cli.main([])

    assert exit_code == 0
    launch_mock.assert_called_once()


