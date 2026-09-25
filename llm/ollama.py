import json
import re
from typing import Optional, Any, Dict, Union
import ollama
from llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama implementation of LLMProvider."""

    def __init__(self, model_name: str = "qwen2.5-coder:1.5b", host: Optional[str] = None):
        self.model_name = model_name
        self.host = host
        if host:
            self.client = ollama.Client(host=host)
        else:
            self.client = ollama.Client()

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.0,
        response_format: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> str:
        """Invokes Ollama model and returns text output."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        options = {"temperature": temperature}

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "options": options,
        }

        if response_format is not None:
            kwargs["format"] = response_format

        response = self.client.chat(**kwargs)
        content = response.message.content or ""
        return content

    @staticmethod
    def extract_code(text: str) -> str:
        """Extracts python code from markdown fences, or returns trimmed raw text."""
        # Check for ```python ... ```
        pattern_py = r"```python\s*(.*?)\s*```"
        match_py = re.search(pattern_py, text, re.DOTALL)
        if match_py:
            return match_py.group(1).strip()

        # Check for generic ``` ... ```
        pattern_gen = r"```\s*(.*?)\s*```"
        match_gen = re.search(pattern_gen, text, re.DOTALL)
        if match_gen:
            return match_gen.group(1).strip()

        return text.strip()

    @staticmethod
    def extract_json(text: str) -> Dict[str, Any]:
        """Extracts and parses JSON object from response text."""
        text = text.strip()
        # Direct parse attempt
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting code block
        extracted = OllamaProvider.extract_code(text)
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass

        # Search for first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            substring = text[start : end + 1]
            return json.loads(substring)

        raise ValueError(f"Could not parse valid JSON from text: {text[:200]}")
