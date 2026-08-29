"""
C++ Compiler Module.

Handles compilation of C++ source files into executable binaries locally or
inside a hardened Docker container using g++.
"""

import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from sandbox_policy import (
    DEFAULT_COMPILER_FLAGS,
    DEFAULT_SANDBOX_POLICY,
    CompileLimits,
    SandboxPolicy,
)


@dataclass(frozen=True)
class CompileResult:
    """
    Structured compilation output metrics and result flags.
    """
    success: bool
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool
    oom_killed: bool = False
    is_docker_system_error: bool = False
    error_message: Optional[str] = None


def compile_cpp_docker(
    workspace_dir: Union[str, Path],
    policy: Optional[SandboxPolicy] = None,
    limits: Optional[CompileLimits] = None,
) -> CompileResult:
    """
    Compiles /sandbox/source.cpp into /sandbox/main inside a Docker container.

    Args:
        workspace_dir: Host directory path containing source.cpp.
        policy: Sandbox policy configuring security flags and runner image.
        limits: Compile limits (timeout and output cap).

    Returns:
        CompileResult detailing success, stdout, stderr, timing, and errors.
    """
    if policy is None:
        policy = DEFAULT_SANDBOX_POLICY
    if limits is None:
        limits = policy.compile_limits

    ws_path = Path(workspace_dir).resolve()
    container_name = f"judge-compile-{uuid.uuid4().hex[:12]}"

    # Build docker run command for compilation (mounting workspace as read-write /sandbox:rw)
    docker_args = policy.to_docker_args(
        container_name=container_name,
        workspace_dir=ws_path,
        mount_read_only=False,
    )

    compiler_cmd = [
        policy.runner_image,
        "g++",
    ] + DEFAULT_COMPILER_FLAGS + [
        "/sandbox/source.cpp",
        "-o",
        "/sandbox/main",
    ]

    full_cmd = docker_args + compiler_cmd

    start_time = time.monotonic()
    timed_out = False
    stdout_str = ""
    stderr_str = ""
    error_msg: Optional[str] = None
    is_system_error = False
    oom_killed = False

    try:
        proc = subprocess.run(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=limits.timeout_s,
            check=False,
            text=True,
        )
        duration_ms = (time.monotonic() - start_time) * 1000.0

        stdout_str = (proc.stdout or "")[: limits.max_output_bytes]
        stderr_str = (proc.stderr or "")[: limits.max_output_bytes]

        # Check for Docker CLI launch error (exit code 125)
        if proc.returncode == 125:
            is_system_error = True
            error_msg = f"Docker container launch failed: {stderr_str.strip() or 'Docker CLI returned exit code 125.'}"
            return CompileResult(
                success=False,
                stdout=stdout_str,
                stderr=stderr_str,
                duration_ms=round(duration_ms, 2),
                timed_out=False,
                oom_killed=False,
                is_docker_system_error=True,
                error_message=error_msg,
            )

        # Inspect if compiler process was OOMKilled
        oom_killed = _inspect_compile_oom_killed(container_name)

        binary_path = ws_path / "main"
        success = (proc.returncode == 0) and binary_path.exists() and not oom_killed

        if oom_killed:
            error_msg = "Compilation failed: Compiler exceeded memory limit."
        elif not success and proc.returncode != 0:
            error_msg = f"Compilation failed inside Docker container (exit code {proc.returncode})."

        return CompileResult(
            success=success,
            stdout=stdout_str,
            stderr=stderr_str,
            duration_ms=round(duration_ms, 2),
            timed_out=False,
            oom_killed=oom_killed,
            is_docker_system_error=False,
            error_message=error_msg,
        )

    except subprocess.TimeoutExpired as e:
        duration_ms = (time.monotonic() - start_time) * 1000.0
        _kill_and_remove_container(container_name)

        stdout_captured = (e.stdout or "").decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr_captured = (e.stderr or "").decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")

        return CompileResult(
            success=False,
            stdout=stdout_captured[: limits.max_output_bytes],
            stderr=stderr_captured[: limits.max_output_bytes],
            duration_ms=round(duration_ms, 2),
            timed_out=True,
            oom_killed=False,
            is_docker_system_error=False,
            error_message=f"Docker compilation timed out after {limits.timeout_s} seconds.",
        )

    except FileNotFoundError:
        duration_ms = (time.monotonic() - start_time) * 1000.0
        return CompileResult(
            success=False,
            stdout="",
            stderr="",
            duration_ms=round(duration_ms, 2),
            timed_out=False,
            oom_killed=False,
            is_docker_system_error=True,
            error_message="Docker CLI binary not found on host system.",
        )

    except Exception as ex:
        duration_ms = (time.monotonic() - start_time) * 1000.0
        return CompileResult(
            success=False,
            stdout="",
            stderr="",
            duration_ms=round(duration_ms, 2),
            timed_out=False,
            oom_killed=False,
            is_docker_system_error=True,
            error_message=f"Docker compilation process error: {str(ex)}",
        )

    finally:
        _kill_and_remove_container(container_name)


def compile_cpp(
    source_path: Union[str, Path],
    output_path: Union[str, Path],
    limits: Optional[CompileLimits] = None,
    use_docker: bool = False,
    policy: Optional[SandboxPolicy] = None,
) -> CompileResult:
    """
    Main compilation interface supporting both Docker and local execution.
    """
    if use_docker:
        src_parent = Path(source_path).resolve().parent
        return compile_cpp_docker(workspace_dir=src_parent, policy=policy, limits=limits)

    if limits is None:
        limits = CompileLimits()

    src = Path(source_path).resolve()
    out = Path(output_path).resolve()
    cwd = src.parent

    cmd: List[str] = ["g++"] + DEFAULT_COMPILER_FLAGS + [str(src), "-o", str(out)]

    start_time = time.monotonic()

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=limits.timeout_s,
            check=False,
            text=True,
        )
        duration_ms = (time.monotonic() - start_time) * 1000.0

        stdout_str = (proc.stdout or "")[: limits.max_output_bytes]
        stderr_str = (proc.stderr or "")[: limits.max_output_bytes]
        sanitized_stderr = stderr_str.replace(str(src), "source.cpp").replace(str(cwd), ".")

        success = (proc.returncode == 0) and out.exists()
        error_msg = f"Compilation failed with exit code {proc.returncode}." if not success else None

        return CompileResult(
            success=success,
            stdout=stdout_str,
            stderr=sanitized_stderr,
            duration_ms=round(duration_ms, 2),
            timed_out=False,
            oom_killed=False,
            is_docker_system_error=False,
            error_message=error_msg,
        )

    except subprocess.TimeoutExpired as e:
        duration_ms = (time.monotonic() - start_time) * 1000.0
        stdout_captured = (e.stdout or "").decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr_captured = (e.stderr or "").decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")

        return CompileResult(
            success=False,
            stdout=stdout_captured[: limits.max_output_bytes],
            stderr=stderr_captured[: limits.max_output_bytes],
            duration_ms=round(duration_ms, 2),
            timed_out=True,
            oom_killed=False,
            is_docker_system_error=False,
            error_message=f"Compilation timed out after {limits.timeout_s} seconds.",
        )

    except FileNotFoundError:
        duration_ms = (time.monotonic() - start_time) * 1000.0
        return CompileResult(
            success=False,
            stdout="",
            stderr="",
            duration_ms=round(duration_ms, 2),
            timed_out=False,
            oom_killed=False,
            is_docker_system_error=True,
            error_message="g++ compiler binary not found on host system.",
        )

    except Exception as ex:
        duration_ms = (time.monotonic() - start_time) * 1000.0
        return CompileResult(
            success=False,
            stdout="",
            stderr="",
            duration_ms=round(duration_ms, 2),
            timed_out=False,
            oom_killed=False,
            is_docker_system_error=True,
            error_message=f"Compilation process failure: {str(ex)}",
        )


def _inspect_compile_oom_killed(container_name: str) -> bool:
    """Checks if the compile container was OOMKilled."""
    try:
        res = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.OOMKilled}}", container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3.0,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip().lower() == "true":
            return True
    except Exception:
        pass
    return False


def _kill_and_remove_container(container_name: str) -> None:
    """Helper to remove container without raising exceptions."""
    try:
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5.0,
            check=False,
        )
    except Exception:
        pass
