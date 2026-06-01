# tests/test_cli.py
from typer.testing import CliRunner
from cli.main import app

runner = CliRunner()


def test_app_has_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "NEXUS" in result.output


def test_ask_command_exists():
    result = runner.invoke(app, ["ask", "--help"])
    assert result.exit_code == 0


def test_chat_command_exists():
    result = runner.invoke(app, ["chat", "--help"])
    assert result.exit_code == 0


def test_doctor_command_exists():
    result = runner.invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0


def test_note_command_exists():
    result = runner.invoke(app, ["note", "--help"])
    assert result.exit_code == 0


def test_log_command_exists():
    result = runner.invoke(app, ["log", "--help"])
    assert result.exit_code == 0


def test_sync_command_exists():
    result = runner.invoke(app, ["sync", "--help"])
    assert result.exit_code == 0


def test_digest_command_exists():
    result = runner.invoke(app, ["digest", "--help"])
    assert result.exit_code == 0


def test_connect_command_exists():
    result = runner.invoke(app, ["connect", "--help"])
    assert result.exit_code == 0
