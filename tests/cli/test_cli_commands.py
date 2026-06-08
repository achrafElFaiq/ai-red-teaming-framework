from types import SimpleNamespace
from unittest.mock import patch

from redteaming.cli import dashboard as dashboard_cli
from redteaming.cli import main as cli_main


def test_main_dispatches_run_subcommand():
    with patch("redteaming.cli.main.run_main", return_value=3) as run_main_mock:
        exit_code = cli_main.main(["run", "campaign.yaml", "--skip-checks"])

    assert exit_code == 3
    run_main_mock.assert_called_once_with(["campaign.yaml", "--skip-checks"], prog="redteaming run")


def test_main_dispatches_dashboard_subcommand():
    with patch("redteaming.cli.main.dashboard_main", return_value=0) as dash_mock:
        exit_code = cli_main.main(["dashboard"])

    assert exit_code == 0
    dash_mock.assert_called_once_with([])


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
    exit_code = cli_main.main(["blah"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "unknown command" in captured.err


def test_dashboard_main_launches_dashboard_and_returns_zero():
    with patch("redteaming.cli.dashboard.configure_logging"), patch(
        "redteaming.cli.dashboard.launch_dashboard"
    ) as launch_mock:
        exit_code = dashboard_cli.main([])

    assert exit_code == 0
    launch_mock.assert_called_once()
