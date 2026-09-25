from typing import Protocol, Optional, Any, Dict, Union


class LLMProvider(Protocol):
    """Protocol for model-agnostic LLM providers."""

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.0,
        response_format: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> str:
        """Generates a text completion given system and user prompts."""
        ...
