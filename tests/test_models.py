from domain.enums import RunStatus, ErrorType, ExecutionMode
from domain.models import TaskSpecification, ExecutionResult, Attempt, RunResult


def test_task_specification_defaults():
    spec = TaskSpecification()
    assert spec.language == "python"
    assert spec.execution_mode == ExecutionMode.SCRIPT.value
    assert spec.entrypoint == "main.py"
    assert spec.dependencies == []
    assert spec.tests_required is False


def test_execution_result_is_success():
    success_result = ExecutionResult(
        exit_code=0,
        stdout="Hello World",
        stderr="",
        duration_ms=45,
        timed_out=False,
    )
    assert success_result.is_success is True

    failure_result = ExecutionResult(
        exit_code=1,
        stdout="",
        stderr="ZeroDivisionError",
        duration_ms=50,
        timed_out=False,
    )
    assert failure_result.is_success is False

    timed_out_result = ExecutionResult(
        exit_code=0,
        stdout="",
        stderr="Timeout",
        duration_ms=30000,
        timed_out=True,
    )
    assert timed_out_result.is_success is False


def test_run_result():
    res = RunResult(
        run_id="run_123",
        status=RunStatus.VERIFIED,
        attempts=[],
        final_source="print('hello')",
        total_attempts=1,
        message="All good",
    )
    assert res.status == RunStatus.VERIFIED
    assert res.total_attempts == 1
