from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from domain.enums import RunStatus, ErrorType, ExecutionMode


@dataclass
class TaskSpecification:
    """Structured specification produced by Planner."""
    language: str = "python"
    execution_mode: str = ExecutionMode.SCRIPT.value
    entrypoint: str = "main.py"
    dependencies: list[str] = field(default_factory=list)
    input_files: list[str] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    tests_required: bool = False
    network_required: bool = False
    description: str = ""


@dataclass
class ExecutionResult:
    """Outcome of executing generated code in sandbox."""
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
    resource_limit_exceeded: bool = False
    signal: Optional[int] = None

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and not self.resource_limit_exceeded


@dataclass
class Attempt:
    """Audit record for a single execution and self-healing cycle."""
    id: str
    run_id: str
    attempt_number: int
    state_before: str
    state_after: str
    source_code: str
    execution_result: Optional[ExecutionResult] = None
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None
    repair_summary: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


@dataclass
class AgentState:
    """Mutable runtime state during orchestration."""
    run_id: str
    task: str
    language: str = "python"
    execution_mode: str = ExecutionMode.SCRIPT.value
    workspace: str = ""
    source: str = ""
    specification: Optional[TaskSpecification] = None
    attempt: int = 0
    max_attempts: int = 5
    errors: list[dict] = field(default_factory=list)
    status: RunStatus = RunStatus.PENDING


@dataclass
class RunResult:
    """Final result returned by Orchestrator."""
    run_id: str
    status: RunStatus
    attempts: list[Attempt]
    final_source: Optional[str] = None
    total_attempts: int = 0
    execution_result: Optional[ExecutionResult] = None
    message: str = ""
