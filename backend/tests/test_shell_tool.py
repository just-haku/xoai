import asyncio

from xoai.agents.tools import shell


def test_execute_command_rejects_non_allowlisted_binaries():
    result = asyncio.run(shell.execute_command("u1", "rm -rf /tmp/demo"))
    assert "not allowed" in result


def test_execute_command_uses_argument_runner(monkeypatch, tmp_path):
    calls = {}

    def fake_run(args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return type("Result", (), {"stdout": "ok\n", "stderr": ""})()

    monkeypatch.setattr(shell, "get_user_workspace", lambda user_id: str(tmp_path))
    monkeypatch.setattr(shell, "get_user_venv", lambda user_id: str(tmp_path / ".venv"))
    monkeypatch.setattr(shell.subprocess, "run", fake_run)

    result = asyncio.run(shell.execute_command("u1", "python --version"))

    assert result == "ok"
    assert calls["args"] == ["python", "--version"]
    assert calls["kwargs"]["cwd"] == str(tmp_path)
    assert str(tmp_path / ".venv" / "bin") in calls["kwargs"]["env"]["PATH"]

