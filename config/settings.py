from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    """Application configuration for Phase 1."""
    model_name: str = "qwen2.5-coder:1.5b"
    max_attempts: int = 5
    execution_timeout_seconds: int = 30
    network_enabled: bool = False
    workspace_root: Path = Path("./workspaces")
    keep_workspaces: bool = True
