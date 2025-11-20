# Workspace Core

Programmatic builder for VS Code workspace files (`.code-workspace`) with layered configuration support.

## Overview
- Creates or updates `.code-workspace` files safely
- Uses a step-based builder pattern to compose workspace settings from multiple sources
- Handles nested JSON structure ensuring keys exist with defaults
- Validates file extensions and permissions

## Features
- **Step-based construction** – Add steps to modify specific parts of the workspace JSON
- **Deep merging** – Ensures nested keys exist before applying updates via `TargetLayer`
- **Safe persistence** – Validates JSON serializability and handles IO errors
- **Auto-creation** – Creates the workspace file if it doesn't exist

## Quickstart

```python
from cores.workspace_core.workspace_builder import WorkspaceBuilder, WorkspaceBuildingStep, TargetLayer

# Initialize builder (defaults to <cwd_name>.code-workspace if path omitted)
builder = WorkspaceBuilder("my-project.code-workspace")

# Add folders to the workspace (Root level)
builder.add_step(
    WorkspaceBuildingStep(
        target=[], 
        content={"folders": [{"path": "."}, {"path": "./libs"}]}
    )
)

# Add python settings (Nested under "settings")
builder.add_step(
    WorkspaceBuildingStep(
        target=[TargetLayer("settings", {})],
        content={"python.analysis.typeCheckingMode": "basic"}
    )
)

# Build and save
data = builder.build_workspace()
builder.write_workspace(data)
```

## API

```python
@dataclass
class TargetLayer:
    target: str
    default: Dict | List

@dataclass
class WorkspaceBuildingStep:
    target: List[TargetLayer]
    content: Dict

class WorkspaceBuilder:
    def __init__(self, workspace_path: Optional[Union[str, Path]] = None) -> None: ...
    def add_step(self, step: WorkspaceBuildingStep) -> None: ...
    def clear_steps(self) -> None: ...
    def build_workspace(self) -> Dict: ...
    def write_workspace(self, workspace_data: Dict) -> None: ...
```

## Notes
- `TargetLayer` allows you to drill down into the JSON structure (e.g., `settings` -> `python`).
- `WorkspaceBuildingStep` applies the `content` dict to the target location.
- The builder validates that the file extension is `.code-workspace`.

## Requirements & prerequisites
- Python standard library (`json`, `pathlib`)
- `utils.logger_util` for logging
- `cores.exceptions_core` for error handling

## Troubleshooting
- **`ValueError: Invalid workspace file extension`** – Ensure your path ends with `.code-workspace`.
- **`ADHDError: Unable to write workspace file`** – Check file permissions and disk space.
- **Settings not appearing** – Ensure your `TargetLayer` chain correctly points to the desired nesting level.

## Module structure

```
cores/workspace_core/
├─ __init__.py             # package marker
├─ workspace_builder.py    # Main builder logic
├─ init.yaml               # module metadata
└─ README.md               # this file
```

## See also
- Project Init Core – Uses this module to generate the initial workspace during project setup
- Config Manager – Manages configuration that might be injected into the workspace
