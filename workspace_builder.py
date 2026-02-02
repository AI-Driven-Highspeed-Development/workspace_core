from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from logger_util import Logger
from exceptions_core import ADHDError

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
        self.logger = Logger(name=type(self).__name__)
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
        
        self.steps: List[WorkspaceBuildingStep] = []
        
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


def generate_workspace_file(
    modules_data: List[Dict[str, Any]],
    root_path: Path,
    workspace_path: Optional[Path] = None,
) -> Path:
    """Generate a VS Code workspace file from pre-filtered module data.
    
    This is the public API for workspace generation. The caller is responsible
    for filtering which modules should be included based on visibility rules.
    
    Args:
        modules_data: List of module dicts, each with 'path' (Path or str) key.
                     The path should be absolute or relative to root_path.
        root_path: The project root path (used for relative path calculation).
        workspace_path: Optional explicit path for the workspace file.
                       Defaults to root_path / "{root_name}.code-workspace".
    
    Returns:
        Path to the generated workspace file.
    
    Raises:
        ADHDError: If workspace file cannot be created or written.
    """
    logger = Logger(name="generate_workspace_file")
    root_path = Path(root_path).resolve()
    
    if workspace_path is None:
        workspace_path = root_path / f"{root_path.name}.code-workspace"
    else:
        workspace_path = Path(workspace_path).resolve()
    
    folder_entries: List[Dict[str, str]] = []
    seen_paths: set[str] = set()
    
    for module in modules_data:
        module_path = module.get("path")
        if module_path is None:
            continue
        
        module_path = Path(module_path)
        if not module_path.is_absolute():
            module_path = root_path / module_path
        
        try:
            relative_path = module_path.relative_to(root_path)
        except ValueError:
            logger.warning(
                f"Module path {module_path} is not under project root {root_path}. Skipping workspace entry."
            )
            continue
        
        folder_path = f"./{relative_path.as_posix()}"
        if folder_path not in seen_paths:
            folder_entries.append({"path": folder_path})
            seen_paths.add(folder_path)
    
    # Always include root folder
    if "." not in seen_paths:
        folder_entries.append({"path": "."})
    
    builder = WorkspaceBuilder(str(workspace_path))
    builder.add_step(
        WorkspaceBuildingStep(
            target=[],
            content={
                "folders": folder_entries,
                "settings": {
                    "python.analysis.extraPaths": [
                        root_path.as_posix(),
                    ],
                },
            },
        )
    )
    workspace_data = builder.build_workspace()
    builder.write_workspace(workspace_data)
    logger.info(f"Workspace file created at {workspace_path}")
    return workspace_path