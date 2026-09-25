import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional
from domain.models import ExecutionResult


def run_process(
    command: List[str],
    cwd: Path,
    env: Optional[Dict[str, str]] = None,
    timeout_seconds: int = 30,
) -> ExecutionResult:
    """Executes a command in a child process with timeout and output capture."""
    start_time = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return ExecutionResult(
            exit_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            duration_ms=duration_ms,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\nProcess timed out after {timeout_seconds} seconds."
        return ExecutionResult(
            exit_code=-1,
            stdout=stdout,
            stderr=stderr.strip(),
            duration_ms=duration_ms,
            timed_out=True,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return ExecutionResult(
            exit_code=-1,
            stdout="",
            stderr=f"Process execution error: {str(exc)}",
            duration_ms=duration_ms,
            timed_out=False,
        )
