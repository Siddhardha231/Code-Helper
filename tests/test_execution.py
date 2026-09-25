import sys
import tempfile
from pathlib import Path
from execution.sandbox import ExecutionSandbox
from execution.process import run_process


def test_syntax_checker():
    sandbox = ExecutionSandbox()

    valid_code = "print('Hello, valid world!')\nx = 10 + 20"
    assert sandbox.check_syntax(valid_code) is None

    invalid_code = "def bad_func(:\n    pass"
    syntax_err = sandbox.check_syntax(invalid_code)
    assert syntax_err is not None
    assert "SyntaxError" in syntax_err


def test_sandbox_execution_success(tmp_path):
    sandbox = ExecutionSandbox(timeout_seconds=5)
    script_path = tmp_path / "main.py"
    script_path.write_text("print('Execution verified')", encoding="utf-8")

    result = sandbox.execute(workspace_path=tmp_path, entrypoint="main.py")
    assert result.is_success is True
    assert result.exit_code == 0
    assert "Execution verified" in result.stdout
    assert result.stderr == ""


def test_sandbox_execution_syntax_error(tmp_path):
    sandbox = ExecutionSandbox(timeout_seconds=5)
    script_path = tmp_path / "main.py"
    script_path.write_text("print('broken syntax", encoding="utf-8")

    result = sandbox.execute(workspace_path=tmp_path, entrypoint="main.py")
    assert result.is_success is False
    assert result.exit_code == 1
    assert "SyntaxError" in result.stderr


def test_sandbox_execution_runtime_error(tmp_path):
    sandbox = ExecutionSandbox(timeout_seconds=5)
    script_path = tmp_path / "main.py"
    script_path.write_text("x = 1 / 0", encoding="utf-8")

    result = sandbox.execute(workspace_path=tmp_path, entrypoint="main.py")
    assert result.is_success is False
    assert result.exit_code != 0
    assert "ZeroDivisionError" in result.stderr


def test_sandbox_timeout(tmp_path):
    sandbox = ExecutionSandbox(timeout_seconds=1)
    script_path = tmp_path / "main.py"
    script_path.write_text("import time\ntime.sleep(3)\nprint('Done')", encoding="utf-8")

    result = sandbox.execute(workspace_path=tmp_path, entrypoint="main.py", timeout=1)
    assert result.timed_out is True
    assert result.is_success is False
    assert "timed out" in result.stderr.lower()
