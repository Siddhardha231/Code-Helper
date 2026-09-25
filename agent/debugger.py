from pathlib import Path
from typing import Optional, List
from domain.models import TaskSpecification, Attempt
from llm.base import LLMProvider
from llm.ollama import OllamaProvider


class Debugger:
    """Agent that analyzes errors/tracebacks and repairs Python code."""

    def __init__(self, llm: LLMProvider, prompt_path: Optional[Path] = None):
        self.llm = llm
        if prompt_path is None:
            prompt_path = Path(__file__).parent.parent / "prompts" / "debugger.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    def repair(
        self,
        specification: TaskSpecification,
        current_code: str,
        error_message: str,
        prior_attempts: Optional[List[Attempt]] = None,
    ) -> str:
        """Repairs failing source code using traceback and error context."""
        history_summary = ""
        if prior_attempts:
            lines = []
            for att in prior_attempts:
                lines.append(f"Attempt #{att.attempt_number}: Error: {att.error_message or 'Unknown'}")
            history_summary = "\n".join(lines)

        user_message = (
            f"Original Task: {specification.description}\n\n"
            f"Current Code in `{specification.entrypoint}`:\n"
            f"```python\n{current_code}\n```\n\n"
            f"Execution Error / Traceback:\n"
            f"```text\n{error_message}\n```\n"
        )

        if history_summary:
            user_message += f"\nPrior Attempts History:\n{history_summary}\n"

        user_message += (
            f"\nPlease diagnose the error and provide the complete, corrected `{specification.entrypoint}`."
        )

        response = self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_message,
            temperature=0.1,
        )

        fixed_code = OllamaProvider.extract_code(response)
        return fixed_code
