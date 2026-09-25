import os
import sys
import traceback
from pathlib import Path
from typing import Optional, Dict
from domain.models import ExecutionResult
from execution.process import run_process
from execution.timeout import DEFAULT_TIMEOUT_SECONDS


class ExecutionSandbox:
    """Phase 1 Execution Sandbox enforcing workspace directory isolation and timeouts."""

    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS):
        self.timeout_seconds = timeout_seconds

    def check_syntax(self, source_code: str, filename: str = "main.py") -> Optional[str]:
        """Performs a deterministic Python syntax validation check.
        Returns None if syntax is valid, or the formatted syntax error traceback.
        """
        try:
            compile(source_code, filename, "exec")
            return None
        except SyntaxError as e:
            tb = traceback.format_exception_only(type(e), e)
            return "".join(tb).strip()

    def build_environment(self) -> Dict[str, str]:
        """Creates a sanitized environment for script execution."""
        clean_env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "TEMP": os.environ.get("TEMP", ""),
            "TMP": os.environ.get("TMP", ""),
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        # In Linux/Unix or Windows, ensure PATHEXT is available for Windows binary lookup
        if "PATHEXT" in os.environ:
            clean_env["PATHEXT"] = os.environ["PATHEXT"]
        return clean_env

    def execute(
        self,
        workspace_path: Path,
        entrypoint: str = "main.py",
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """Executes the entrypoint script inside the isolated workspace."""
        file_path = workspace_path / entrypoint
        if not file_path.exists():
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=f"FileNotFoundError: Entrypoint '{entrypoint}' not found in workspace {workspace_path}",
                duration_ms=0,
                timed_out=False,
            )

        # 1. Deterministic syntax validation check
        with open(file_path, "r", encoding="utf-8") as f:
            code_content = f.read()

        syntax_err = self.check_syntax(code_content, entrypoint)
        if syntax_err:
            return ExecutionResult(
                exit_code=1,
                stdout="",
                stderr=syntax_err,
                duration_ms=0,
                timed_out=False,
            )

        # 2. Run Python in subprocess
        cmd = [sys.executable, str(file_path.name)]
        env = self.build_environment()
        timeout_to_use = timeout or self.timeout_seconds

        return run_process(
            command=cmd,
            cwd=workspace_path,
            env=env,
            timeout_seconds=timeout_to_use,
        )
