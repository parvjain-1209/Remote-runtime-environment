"""
Sandbox Policy Configuration for GDG Remote Runtime.

This module acts as the SINGLE SOURCE OF TRUTH for container and sandbox
execution security boundaries, limits, constants, and Docker argument construction.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

# Centralized constants across the application
DEFAULT_SOURCE_CODE_MAX_BYTES: int = 64 * 1024  # 64 KB max source code size
DEFAULT_COMPILER_FLAGS: List[str] = ["-std=c++17", "-O2"]


@dataclass(frozen=True)
class CompileLimits:
    """
    Limits applied specifically during source code compilation.
    """
    timeout_s: float = 10.0
    max_output_bytes: int = 64 * 1024  # 64 KB max compiler stdout/stderr capture


@dataclass(frozen=True)
class ExecutionLimits:
    """
    Limits applied during binary execution against testcases.
    """
    timeout_s: float = 2.0
    max_output_bytes: int = 1024 * 1024  # 1 MB max binary stdout/stderr capture


@dataclass(frozen=True)
class SandboxPolicy:
    """
    Configuration parameters defining security and resource constraints
    for sandbox execution.
    """

    # Resource Limits
    cpu_limit: float = 1.0                # Limit to 1 CPU core
    memory_limit: str = "256m"            # 256 MB maximum RAM
    memory_swap: str = "256m"             # Disables extra swap memory beyond RAM
    pids_limit: int = 64                  # Prevents process/fork bombs
    tmpfs_size: str = "64m"               # 64 MB read-write in-memory tmpfs at /tmp

    # Timeouts (seconds)
    execution_timeout_seconds: float = 2.0  # Max runtime for user binary
    compilation_timeout_seconds: float = 10.0 # Max runtime for compiler (g++)

    # Output Limits
    max_output_bytes: int = 1024 * 1024   # 1 MB max stdout/stderr capture

    # Security Isolation Flags & Options
    network_disabled: bool = True          # Equivalent to --network none
    read_only_root_fs: bool = True         # Equivalent to --read-only
    cap_drop: List[str] = field(default_factory=lambda: ["ALL"]) # Drops all Linux capabilities
    no_new_privileges: bool = True         # --security-opt=no-new-privileges
    execution_user: str = "1000:1000"      # Non-root user (uid:gid 1000:1000) inside container
    runner_image: str = "gdg-runner:latest" # Deterministic runner image tag
    ulimit_nofile: int = 64                # Max open file descriptors
    ulimit_core: int = 0                   # Disables core dumps

    @property
    def compile_limits(self) -> CompileLimits:
        """Derive compile limits from policy defaults."""
        return CompileLimits(
            timeout_s=self.compilation_timeout_seconds,
            max_output_bytes=64 * 1024,
        )

    @property
    def execution_limits(self) -> ExecutionLimits:
        """Derive execution limits from policy defaults."""
        return ExecutionLimits(
            timeout_s=self.execution_timeout_seconds,
            max_output_bytes=self.max_output_bytes,
        )

    def to_docker_args(
        self,
        container_name: str,
        workspace_dir: Union[str, Path],
        mount_read_only: bool = True,
        host_workspace_dir_override: Optional[str] = None,
    ) -> List[str]:
        """
        Constructs the exact docker run argument array for spawning a sandboxed container.
        Resolves container workspace paths to host workspace paths for Docker-out-of-Docker compatibility.

        Args:
            container_name: Deterministic container name (judge-{sub_id}-{idx}-{uuid}).
            workspace_dir: Workspace directory path inside worker container.
            mount_read_only: If True, mounts workspace as /sandbox:ro; if False, as /sandbox:rw.
            host_workspace_dir_override: Optional host workspace directory override.

        Returns:
            List of command line string arguments for subprocess call to 'docker'.
        """
        worker_ws = Path(workspace_dir).resolve()
        
        host_ws_base = (
            host_workspace_dir_override
            or os.getenv("HOST_WORKSPACE_DIR", "").strip()
            or str(Path.cwd().resolve() / "runtime-workspaces")
        )
        
        worker_ws_base = os.getenv("WORKER_WORKSPACE_DIR", "").strip()
        if not worker_ws_base and str(worker_ws).startswith("/runtime-workspaces"):
            worker_ws_base = "/runtime-workspaces"

        # Resolve host path if worker runs inside Docker-out-of-Docker container
        if worker_ws_base and str(worker_ws).startswith(worker_ws_base):
            rel_sub_path = str(worker_ws)[len(worker_ws_base):].lstrip("/")
            resolved_host_path = str(Path(host_ws_base).resolve() / rel_sub_path)
        else:
            resolved_host_path = str(worker_ws)

        mount_mode = "ro" if mount_read_only else "rw"
        mount_arg = f"{resolved_host_path}:/sandbox:{mount_mode}"

        args = [
            "docker", "run",
            "-i",  # Interactive mode to allow streaming stdin
            "--name", container_name,
            "--network", "none" if self.network_disabled else "bridge",
            "--tmpfs", f"/tmp:rw,noexec,nosuid,nodev,size={self.tmpfs_size}",
            f"--memory={self.memory_limit}",
            f"--memory-swap={self.memory_swap}",
            f"--cpus={self.cpu_limit}",
            f"--pids-limit={self.pids_limit}",
            f"--cap-drop={','.join(self.cap_drop)}",
            "--ulimit", f"nofile={self.ulimit_nofile}:{self.ulimit_nofile}",
            "--ulimit", f"core={self.ulimit_core}:{self.ulimit_core}",
            "--user", self.execution_user,
            "-v", mount_arg,
            "-w", "/sandbox",
        ]

        if self.read_only_root_fs:
            args.append("--read-only")

        if self.no_new_privileges:
            args.append("--security-opt=no-new-privileges")

        return args

    def to_docker_host_config(self) -> Dict[str, object]:
        """
        Returns a serializable dictionary representation of the sandbox policy.
        """
        return {
            "cpus": self.cpu_limit,
            "memory": self.memory_limit,
            "memory_swap": self.memory_swap,
            "pids_limit": self.pids_limit,
            "tmpfs": {"/tmp": f"rw,noexec,nosuid,nodev,size={self.tmpfs_size}"},
            "network_mode": "none" if self.network_disabled else "bridge",
            "read_only": self.read_only_root_fs,
            "cap_drop": list(self.cap_drop),
            "no_new_privileges": self.no_new_privileges,
            "user": self.execution_user,
            "runner_image": self.runner_image,
            "ulimit_nofile": self.ulimit_nofile,
            "ulimit_core": self.ulimit_core,
            "execution_timeout": self.execution_timeout_seconds,
            "compilation_timeout": self.compilation_timeout_seconds,
            "max_output_bytes": self.max_output_bytes,
        }


# Default global instance of sandbox security policy
DEFAULT_SANDBOX_POLICY = SandboxPolicy()
