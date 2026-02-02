"""workspace_core - VS Code workspace file management.

Provides WorkspaceBuilder for creating and managing .code-workspace files.
"""

from .workspace_builder import (
    WorkspaceBuilder,
    WorkspaceBuildingStep,
    TargetLayer,
    generate_workspace_file,
)

__all__ = ["WorkspaceBuilder", "WorkspaceBuildingStep", "TargetLayer", "generate_workspace_file"]
