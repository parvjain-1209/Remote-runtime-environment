"""
Submission Workspace Lifecycle Helper.

Provides isolated temporary filesystem workspaces for participant submissions.
Guarantees cleanup and enforces file constraints.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator, Optional

from sandbox_policy import DEFAULT_SOURCE_CODE_MAX_BYTES


class WorkspaceError(Exception):
    """Exception raised when workspace operations fail."""
    pass


class SubmissionWorkspace:
    """
    Context manager for a single submission workspace.
    
    Creates a dedicated temporary directory containing:
    - source.cpp (fixed source code path)
    - main (fixed compiled binary path)
    """

    MAX_SOURCE_SIZE_BYTES: int = DEFAULT_SOURCE_CODE_MAX_BYTES

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.getenv("WORKER_WORKSPACE_DIR", "./runtime-workspaces")
        
        # Ensure base directory exists
        Path(base_dir).mkdir(parents=True, exist_ok=True)
        self._base_dir = base_dir
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None
        self.dir_path: Optional[Path] = None

    def __enter__(self) -> "SubmissionWorkspace":
        self._temp_dir = tempfile.TemporaryDirectory(prefix="submission_", dir=self._base_dir)
        self.dir_path = Path(self._temp_dir.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        """Cleans up the temporary directory if it exists."""
        if self.dir_path is not None and self.dir_path.exists():
            try:
                shutil.rmtree(self.dir_path, ignore_errors=True)
            except Exception:
                pass
        if self._temp_dir is not None:
            try:
                self._temp_dir.cleanup()
            except Exception:
                pass
            finally:
                self._temp_dir = None
                self.dir_path = None

    @property
    def source_path(self) -> Path:
        """Fixed path to C++ source code file."""
        if self.dir_path is None:
            raise WorkspaceError("Workspace is not active.")
        return self.dir_path / "source.cpp"

    @property
    def binary_path(self) -> Path:
        """Fixed path to compiled output executable binary."""
        if self.dir_path is None:
            raise WorkspaceError("Workspace is not active.")
        return self.dir_path / "main"

    def write_source(self, code: str) -> Path:
        """
        Enforces size limits and writes source code to source.cpp.
        """
        code_bytes = code.encode("utf-8")
        if len(code_bytes) > self.MAX_SOURCE_SIZE_BYTES:
            raise WorkspaceError(
                f"Source code size ({len(code_bytes)} bytes) exceeds maximum limit "
                f"of {self.MAX_SOURCE_SIZE_BYTES} bytes."
            )
        
        path = self.source_path
        with open(path, "wb") as f:
            f.write(code_bytes)
        return path
