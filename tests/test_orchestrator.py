from typing import Optional, Dict, Any, List
from config.settings import Settings
from domain.enums import RunStatus
from domain.models import RunResult
from execution.sandbox import ExecutionSandbox
from workspace.manager import WorkspaceManager
from agent.orchestrator import AgentOrchestrator
from llm.base import LLMProvider


class MockLLMProvider(LLMProvider):
    """Predictable mock provider for deterministic orchestrator testing."""

    def __init__(self, responses: List[str]):
        self.responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.0,
        response_format: Optional[Any] = None,
    ) -> str:
        self.calls.append({"system": system_prompt, "user": user_prompt})
        if self.responses:
            return self.responses.pop(0)
        return "print('Default mock response')"


def test_orchestrator_success_on_first_attempt(tmp_path):
    # Response 1: Planner JSON
    # Response 2: Coder code
    responses = [
        '{"language": "python", "execution_mode": "script", "entrypoint": "main.py", "description": "Say hello"}',
        "```python\nprint('Hello from test!')\n```",
    ]
    mock_llm = MockLLMProvider(responses)
    settings = Settings(max_attempts=3, workspace_root=tmp_path)
    workspace_mgr = WorkspaceManager(root_dir=tmp_path)
    sandbox = ExecutionSandbox(timeout_seconds=5)

    orchestrator = AgentOrchestrator(
        llm=mock_llm,
        sandbox=sandbox,
        workspace_manager=workspace_mgr,
        settings=settings,
    )

    result = orchestrator.run("Say hello")
    assert result.status == RunStatus.VERIFIED
    assert result.total_attempts == 1
    assert "Hello from test!" in result.execution_result.stdout
    assert len(result.attempts) == 1


def test_orchestrator_self_healing_retry(tmp_path):
    # Response 1: Planner JSON
    # Response 2: Coder code (has ZeroDivisionError)
    # Response 3: Debugger code (fixed)
    responses = [
        '{"language": "python", "execution_mode": "script", "entrypoint": "main.py", "description": "Fix math"}',
        "```python\nresult = 1 / 0\nprint(result)\n```",
        "```python\nresult = 1 / 1\nprint(f'Fixed: {result}')\n```",
    ]
    mock_llm = MockLLMProvider(responses)
    settings = Settings(max_attempts=3, workspace_root=tmp_path)
    workspace_mgr = WorkspaceManager(root_dir=tmp_path)
    sandbox = ExecutionSandbox(timeout_seconds=5)

    orchestrator = AgentOrchestrator(
        llm=mock_llm,
        sandbox=sandbox,
        workspace_manager=workspace_mgr,
        settings=settings,
    )

    events = []
    result = orchestrator.run("Fix math", on_event=lambda ev, data: events.append(ev))

    assert result.status == RunStatus.VERIFIED
    assert result.total_attempts == 2
    assert "Fixed: 1.0" in result.execution_result.stdout
    assert len(result.attempts) == 2
    assert result.attempts[0].error_type.value == "runtime"
    assert "ZeroDivisionError" in result.attempts[0].error_message
    assert result.attempts[1].error_type.value == "none"
    assert "CODE_REPAIRED" in events


def test_orchestrator_max_attempts_reached(tmp_path):
    # Never fixes the bug, repeats 3 times
    responses = [
        '{"language": "python", "execution_mode": "script", "entrypoint": "main.py", "description": "Always fail"}',
        "```python\nx = 1 / 0\n```",
        "```python\nx = 1 / 0\n```",
        "```python\nx = 1 / 0\n```",
    ]
    mock_llm = MockLLMProvider(responses)
    settings = Settings(max_attempts=3, workspace_root=tmp_path)
    workspace_mgr = WorkspaceManager(root_dir=tmp_path)
    sandbox = ExecutionSandbox(timeout_seconds=5)

    orchestrator = AgentOrchestrator(
        llm=mock_llm,
        sandbox=sandbox,
        workspace_manager=workspace_mgr,
        settings=settings,
    )

    result = orchestrator.run("Always fail")
    assert result.status == RunStatus.FAILED
    assert result.total_attempts == 3
    assert len(result.attempts) == 3
    assert "ZeroDivisionError" in result.attempts[-1].error_message


def test_orchestrator_handles_missing_module_and_placeholder_rejection(tmp_path):
    # Attempt 1: Coder generates numpy (ModuleNotFoundError)
    # Attempt 2: Debugger mistakenly outputs placeholder '# your fixed code here' (EmptyCodeError)
    # Attempt 3: Debugger outputs working pure python code (Success)
    responses = [
        '{"language": "python", "execution_mode": "script", "entrypoint": "main.py", "description": "Calculate mean"}',
        "```python\nimport non_existent_package_xyz as nep\nprint(nep.mean([1, 2, 3]))\n```",
        "```python\n# your fixed code here\n```",
        "```python\nnums = [1, 2, 3]\nprint(f'Mean: {sum(nums)/len(nums)}')\n```",
    ]
    mock_llm = MockLLMProvider(responses)
    settings = Settings(max_attempts=4, workspace_root=tmp_path)
    workspace_mgr = WorkspaceManager(root_dir=tmp_path)
    sandbox = ExecutionSandbox(timeout_seconds=5)

    orchestrator = AgentOrchestrator(
        llm=mock_llm,
        sandbox=sandbox,
        workspace_manager=workspace_mgr,
        settings=settings,
    )

    result = orchestrator.run("Calculate mean")

    assert result.status == RunStatus.VERIFIED
    assert result.total_attempts == 3
    assert "Mean: 2.0" in result.execution_result.stdout
    # Check that attempt 1 was categorized as dependency error
    assert result.attempts[0].error_type.value == "dependency"
    # Check that attempt 2 was categorized as empty_code error and NOT verified
    assert result.attempts[1].error_type.value == "empty_code"
    # Check that attempt 3 was verified
    assert result.attempts[2].error_type.value == "none"
