from dataclasses import dataclass
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from managers.config_manager import ConfigManager
from utils.logger_util.logger import Logger
from cores.exceptions_core.adhd_exceptions import ADHDError

@dataclass
class TargetLayer:
    target: str
    default: Dict | List
    

@dataclass
class WorkspaceBuildingStep:
    target: List[TargetLayer]
    content: Dict
    

class WorkspaceBuilder:
    
    def __init__(self, workspace_path: Optional[Union[str, Path]] = None) -> None:
        # Resolve workspace path
        if workspace_path is not None:
            self.workspace_path = Path(workspace_path).resolve()
        else:
            cwd = Path.cwd()
            project_name = cwd.name or "workspace"
            self.workspace_path = cwd / f"{project_name}.code-workspace"

        if not str(self.workspace_path).endswith(".code-workspace"):
            message = "Workspace file should have a .code-workspace extension."
            self.logger.error(message)
            raise ValueError("Invalid workspace file extension.")

        # Ensure parent directory exists
        parent_dir = self.workspace_path.parent
        try:
            parent_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.logger.error(f"Failed to create workspace directory '{parent_dir}': {exc}")
            raise ADHDError(f"Unable to prepare workspace directory: {parent_dir}") from exc

        # Create empty workspace file if it doesn't exist
        if not self.workspace_path.exists():
            self.logger.info(
                f"Workspace file {self.workspace_path} does not exist. Creating a new one."
            )
            try:
                with self.workspace_path.open("w", encoding="utf-8") as f:
                    f.write("{}")  # Create an empty JSON file
            except OSError as exc:
                self.logger.error(f"Failed to create workspace file '{self.workspace_path}': {exc}")
                raise ADHDError(f"Unable to create workspace file: {self.workspace_path}") from exc
        
    def add_step(self, step: WorkspaceBuildingStep) -> None:
        if not isinstance(step, WorkspaceBuildingStep):
            raise TypeError("step must be an instance of WorkspaceBuildingStep")
        self.logger.debug(f"Adding workspace build step targeting {[layer.target for layer in step.target]}")
        self.steps.append(step)
        
    def clear_steps(self) -> None:
        self.steps.clear()
        
    def build_workspace(self) -> Dict:
        """Apply all registered steps and return the final workspace structure."""
        workspace_data: Dict[str, Any] = {}

        if not self.steps:
            self.logger.warning("No workspace build steps defined; generating an empty workspace structure.")

        for step in self.steps:
            try:
                target_keys = [layer.target for layer in step.target]
                defaults = [layer.default for layer in step.target]
                ensured = self._chain_ensure_key(workspace_data, target_keys, defaults)
                if not isinstance(ensured, dict):
                    raise ADHDError(
                        "WorkspaceBuilder step target does not resolve to a mapping; "
                        "cannot apply step content."
                    )
                ensured.update(step.content)
            except Exception as exc:
                self.logger.error(f"Failed to apply workspace build step: {exc}")
                raise

        return workspace_data
    
    def write_workspace(self, workspace_data: Dict) -> None:
        """Persist the workspace JSON structure to disk."""
        try:
            json_content = json.dumps(workspace_data, indent=4)
        except (TypeError, ValueError) as exc:
            self.logger.error(f"Workspace data is not JSON-serializable: {exc}")
            raise ADHDError("Workspace data is not JSON-serializable.") from exc

        try:
            with self.workspace_path.open("w", encoding="utf-8") as f:
                f.write(json_content)
        except OSError as exc:
            self.logger.error(f"Failed to write workspace file '{self.workspace_path}': {exc}")
            raise ADHDError(f"Unable to write workspace file: {self.workspace_path}") from exc
    
    def _ensure_key(self, data: dict, key: str, default_value: Any) -> None:
        if key not in data:
            data[key] = default_value

    def _chain_ensure_key(self, data: dict, keys: List[str], default_value: List[Any]):
        """Ensure nested keys exist with corresponding default values."""
        current: Any = data
        if len(keys) != len(default_value):
            raise ValueError("keys and default_value must have the same length")

        for i, key in enumerate(keys):
            if not isinstance(current, dict):
                raise ADHDError("Intermediate workspace structure is not a mapping while ensuring keys.")
            self._ensure_key(current, key, default_value[i])
            current = current[key]
        return current