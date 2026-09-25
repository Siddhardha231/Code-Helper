from pathlib import Path
from typing import Optional
from domain.models import TaskSpecification
from llm.base import LLMProvider
from llm.ollama import OllamaProvider


class Coder:
    """Agent that produces Python source code for main.py."""

    def __init__(self, llm: LLMProvider, prompt_path: Optional[Path] = None):
        self.llm = llm
        if prompt_path is None:
            prompt_path = Path(__file__).parent.parent / "prompts" / "coder.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    def generate(self, specification: TaskSpecification, user_prompt: str) -> str:
        """Generates source code for main.py based on specification and prompt."""
        user_message = (
            f"User Goal: {user_prompt}\n"
            f"Specification:\n"
            f"- Language: {specification.language}\n"
            f"- Execution Mode: {specification.execution_mode}\n"
            f"- Entrypoint: {specification.entrypoint}\n"
            f"- Description: {specification.description}\n\n"
            f"Please write the complete, standalone Python code for `{specification.entrypoint}`."
        )

        response = self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_message,
            temperature=0.1,
        )

        code = OllamaProvider.extract_code(response)
        return code
