"""
Submission Workspace Lifecycle Helper.

Provides isolated temporary filesystem workspaces for participant submissions.
Supports C++, Python, and Java source files with cloud-resilient temp directory fallbacks.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from sandbox_policy import DEFAULT_SOURCE_CODE_MAX_BYTES


class WorkspaceError(Exception):
    """Exception raised when workspace operations fail."""
    pass


class SubmissionWorkspace:
    """
    Context manager for a single submission workspace.

    Creates a dedicated temporary directory supporting C++, Python, and Java files.
    Includes automated fallback to standard system temp directory for cloud environments (Render/containers).
    """

    MAX_SOURCE_SIZE_BYTES: int = DEFAULT_SOURCE_CODE_MAX_BYTES

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.getenv("WORKER_WORKSPACE_DIR", "")

        target_dir = None
        if base_dir and base_dir.strip():
            try:
                p = Path(base_dir).resolve()
                p.mkdir(parents=True, exist_ok=True)
                test_file = p / f".perm_test_{os.getpid()}"
                test_file.touch()
                test_file.unlink()
                target_dir = str(p)
            except Exception:
                target_dir = None

        if target_dir is None:
            target_dir = tempfile.gettempdir()

        self._base_dir = target_dir
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None
        self.dir_path: Optional[Path] = None

    def __enter__(self) -> "SubmissionWorkspace":
        try:
            self._temp_dir = tempfile.TemporaryDirectory(prefix="submission_", dir=self._base_dir)
        except Exception:
            # Fallback to standard OS temp directory if base_dir creation fails
            self._temp_dir = tempfile.TemporaryDirectory(prefix="submission_")
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

    def get_source_path(self, language: str = "cpp") -> Path:
        """Returns host path to language source code file."""
        if self.dir_path is None:
            raise WorkspaceError("Workspace is not active.")
        lang = language.lower()
        if lang == "python":
            return self.dir_path / "main.py"
        elif lang == "java":
            return self.dir_path / "Main.java"
        return self.dir_path / "source.cpp"

    def get_binary_path(self, language: str = "cpp") -> Path:
        """Returns host path to output binary or target file."""
        if self.dir_path is None:
            raise WorkspaceError("Workspace is not active.")
        lang = language.lower()
        if lang == "python":
            return self.dir_path / "main.py"
        elif lang == "java":
            return self.dir_path / "Main.class"
        return self.dir_path / "main"

    @property
    def source_path(self) -> Path:
        """Backward-compatible C++ source path property."""
        return self.get_source_path("cpp")

    @property
    def binary_path(self) -> Path:
        """Backward-compatible C++ binary path property."""
        return self.get_binary_path("cpp")

    def write_source(self, code: str, language: str = "cpp") -> Path:
        """
        Enforces size limits and writes source code to appropriate file.
        """
        code_bytes = code.encode("utf-8")
        if len(code_bytes) > self.MAX_SOURCE_SIZE_BYTES:
            raise WorkspaceError(
                f"Source code size ({len(code_bytes)} bytes) exceeds maximum limit "
                f"of {self.MAX_SOURCE_SIZE_BYTES} bytes."
            )

        path = self.get_source_path(language)
        with open(path, "wb") as f:
            f.write(code_bytes)
        return path
