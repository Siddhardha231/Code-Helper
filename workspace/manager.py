import shutil
import uuid
from pathlib import Path
from typing import Optional


class WorkspaceManager:
    """Manages isolated run workspaces."""

    def __init__(self, root_dir: Path = Path("./workspaces")):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def create_workspace(self, run_id: Optional[str] = None) -> Path:
        """Creates a dedicated workspace directory for a run."""
        if not run_id:
            run_id = f"ws_{uuid.uuid4().hex[:8]}"
        workspace_path = self.root_dir / run_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        return workspace_path

    def write_source(self, workspace_path: Path, filename: str, content: str) -> Path:
        """Writes source code into the workspace."""
        file_path = workspace_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def read_source(self, workspace_path: Path, filename: str) -> str:
        """Reads source code from the workspace."""
        file_path = workspace_path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"File not found in workspace: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def cleanup(self, workspace_path: Path) -> None:
        """Safely removes a workspace directory."""
        if workspace_path.exists():
            shutil.rmtree(workspace_path, ignore_errors=True)
