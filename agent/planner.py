import json
from pathlib import Path
from typing import Optional
from domain.models import TaskSpecification
from domain.enums import ExecutionMode
from llm.base import LLMProvider
from llm.ollama import OllamaProvider


class Planner:
    """Agent that creates structured TaskSpecification from a natural language prompt."""

    def __init__(self, llm: LLMProvider, prompt_path: Optional[Path] = None):
        self.llm = llm
        if prompt_path is None:
            prompt_path = Path(__file__).parent.parent / "prompts" / "planner.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    def plan(self, user_prompt: str) -> TaskSpecification:
        """Generates a TaskSpecification for the given user prompt."""
        response = self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=f"Create a task specification for the following request:\n\n{user_prompt}",
            temperature=0.0,
            response_format="json",
        )

        try:
            data = OllamaProvider.extract_json(response)
            return TaskSpecification(
                language=data.get("language", "python"),
                execution_mode=data.get("execution_mode", ExecutionMode.SCRIPT.value),
                entrypoint=data.get("entrypoint", "main.py"),
                dependencies=data.get("dependencies", []),
                input_files=data.get("input_files", []),
                output_files=data.get("output_files", []),
                tests_required=data.get("tests_required", False),
                network_required=data.get("network_required", False),
                description=data.get("description", user_prompt),
            )
        except Exception:
            # Deterministic fallback if JSON parsing fails
            return TaskSpecification(
                language="python",
                execution_mode=ExecutionMode.SCRIPT.value,
                entrypoint="main.py",
                description=user_prompt,
            )
