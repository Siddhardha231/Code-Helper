import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any

from config.settings import Settings
from domain.enums import RunStatus, ErrorType
from domain.models import (
    TaskSpecification,
    ExecutionResult,
    Attempt,
    RunResult,
    AgentState,
)
from llm.base import LLMProvider
from execution.sandbox import ExecutionSandbox
from workspace.manager import WorkspaceManager
from agent.planner import Planner
from agent.coder import Coder
from agent.debugger import Debugger


class AgentOrchestrator:
    """Finite State Machine orchestrator managing Phase 1 autonomous code execution lifecycle."""

    def __init__(
        self,
        llm: LLMProvider,
        sandbox: Optional[ExecutionSandbox] = None,
        workspace_manager: Optional[WorkspaceManager] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or Settings()
        self.llm = llm
        self.sandbox = sandbox or ExecutionSandbox(timeout_seconds=self.settings.execution_timeout_seconds)
        self.workspace_manager = workspace_manager or WorkspaceManager(root_dir=self.settings.workspace_root)
        self.planner = Planner(llm=self.llm)
        self.coder = Coder(llm=self.llm)
        self.debugger = Debugger(llm=self.llm)

    def _classify_error(self, execution_result: ExecutionResult) -> ErrorType:
        """Determines the error class from execution output."""
        if execution_result.timed_out:
            return ErrorType.TIMEOUT
        stderr = execution_result.stderr
        if "SyntaxError" in stderr or "IndentationError" in stderr:
            return ErrorType.SYNTAX
        if "PermissionError" in stderr:
            return ErrorType.PERMISSION
        return ErrorType.RUNTIME

    def run(
        self,
        prompt: str,
        on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> RunResult:
        """Executes the complete Phase 1 autonomous code generation & verification loop."""
        run_id = f"run_{uuid.uuid4().hex[:8]}"

        def emit(event_type: str, data: Dict[str, Any]):
            if on_event:
                on_event(event_type, data)

        emit("RUN_STARTED", {"run_id": run_id, "prompt": prompt})

        # 1. Planning State
        emit("STATUS_CHANGED", {"status": RunStatus.PLANNING.value, "message": "Planning task specification..."})
        specification: TaskSpecification = self.planner.plan(prompt)
        emit("PLAN_CREATED", {"specification": specification.__dict__})

        # 2. Coding State
        emit("STATUS_CHANGED", {"status": RunStatus.CODING.value, "message": "Generating Python source code..."})
        current_source: str = self.coder.generate(specification, prompt)
        emit("CODE_GENERATED", {"source": current_source})

        # 3. Create isolated workspace
        workspace_path = self.workspace_manager.create_workspace(run_id=run_id)
        self.workspace_manager.write_source(
            workspace_path=workspace_path,
            filename=specification.entrypoint,
            content=current_source,
        )
        emit("WORKSPACE_PREPARED", {"workspace": str(workspace_path)})

        attempts: List[Attempt] = []
        max_attempts = self.settings.max_attempts
        last_execution_result: Optional[ExecutionResult] = None

        # 4. Execution & Self-Healing Retry Loop
        for attempt_num in range(1, max_attempts + 1):
            attempt_id = f"att_{run_id}_{attempt_num}"
            attempt_started = datetime.now(timezone.utc)

            emit("ATTEMPT_STARTED", {
                "attempt_number": attempt_num,
                "max_attempts": max_attempts,
                "source": current_source,
            })
            emit("STATUS_CHANGED", {
                "status": RunStatus.EXECUTING.value,
                "message": f"Executing code (Attempt {attempt_num}/{max_attempts})...",
            })

            # Sandboxed execution
            execution_result = self.sandbox.execute(
                workspace_path=workspace_path,
                entrypoint=specification.entrypoint,
                timeout=self.settings.execution_timeout_seconds,
            )
            last_execution_result = execution_result

            emit("EXECUTION_COMPLETED", {
                "attempt_number": attempt_num,
                "exit_code": execution_result.exit_code,
                "stdout": execution_result.stdout,
                "stderr": execution_result.stderr,
                "duration_ms": execution_result.duration_ms,
                "timed_out": execution_result.timed_out,
            })

            if execution_result.is_success:
                # Verified!
                attempt_record = Attempt(
                    id=attempt_id,
                    run_id=run_id,
                    attempt_number=attempt_num,
                    state_before=RunStatus.EXECUTING.value,
                    state_after=RunStatus.VERIFIED.value,
                    source_code=current_source,
                    execution_result=execution_result,
                    error_type=ErrorType.NONE,
                    error_message=None,
                    started_at=attempt_started,
                    completed_at=datetime.now(timezone.utc),
                )
                attempts.append(attempt_record)

                emit("STATUS_CHANGED", {
                    "status": RunStatus.VERIFIED.value,
                    "message": f"Code executed successfully on attempt {attempt_num}!",
                })
                emit("RUN_COMPLETED", {"status": RunStatus.VERIFIED.value, "run_id": run_id})

                return RunResult(
                    run_id=run_id,
                    status=RunStatus.VERIFIED,
                    attempts=attempts,
                    final_source=current_source,
                    total_attempts=attempt_num,
                    execution_result=execution_result,
                    message=f"Verified successfully in {attempt_num} attempt(s).",
                )

            # Failure occurred
            err_type = self._classify_error(execution_result)
            err_msg = execution_result.stderr or "Unknown runtime error"

            attempt_record = Attempt(
                id=attempt_id,
                run_id=run_id,
                attempt_number=attempt_num,
                state_before=RunStatus.EXECUTING.value,
                state_after=RunStatus.DEBUGGING.value if attempt_num < max_attempts else RunStatus.FAILED.value,
                source_code=current_source,
                execution_result=execution_result,
                error_type=err_type,
                error_message=err_msg,
                started_at=attempt_started,
                completed_at=datetime.now(timezone.utc),
            )
            attempts.append(attempt_record)

            if attempt_num >= max_attempts:
                # Exhausted all attempts
                emit("STATUS_CHANGED", {
                    "status": RunStatus.FAILED.value,
                    "message": f"Failed after {max_attempts} attempts.",
                })
                emit("RUN_COMPLETED", {"status": RunStatus.FAILED.value, "run_id": run_id})

                return RunResult(
                    run_id=run_id,
                    status=RunStatus.FAILED,
                    attempts=attempts,
                    final_source=current_source,
                    total_attempts=attempt_num,
                    execution_result=execution_result,
                    message=f"Execution failed after maximum {max_attempts} attempts. Check attempt history.",
                )

            # 5. Debugging / Self-Repair
            emit("STATUS_CHANGED", {
                "status": RunStatus.DEBUGGING.value,
                "message": f"Diagnosing error and patching source code (Attempt {attempt_num})...",
            })

            repaired_source = self.debugger.repair(
                specification=specification,
                current_code=current_source,
                error_message=err_msg,
                prior_attempts=attempts,
            )
            attempt_record.repair_summary = "Debugger produced updated source code."

            # Save repaired source into workspace for next attempt
            current_source = repaired_source
            self.workspace_manager.write_source(
                workspace_path=workspace_path,
                filename=specification.entrypoint,
                content=current_source,
            )
            emit("CODE_REPAIRED", {
                "attempt_number": attempt_num,
                "repaired_source": current_source,
            })

        # Fallback (should not be reached)
        return RunResult(
            run_id=run_id,
            status=RunStatus.FAILED,
            attempts=attempts,
            final_source=current_source,
            total_attempts=max_attempts,
            execution_result=last_execution_result,
            message="Terminated after loop completion.",
        )
