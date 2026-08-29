"""
Multi-Language Compiler / Syntax Checker Module.

Handles compilation & syntax validation of C++, Python, and Java source files locally or
inside a hardened Docker container. Includes cloud binary resolution and error logging.
"""

import logging
import os
import shutil
import subprocess
import sys
import time
import traceback
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

logger = logging.getLogger("worker.compiler")


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


def find_executable(binary_name: str, fallback_paths: Optional[List[str]] = None) -> str:
    """
    Resolves binary executable path using shutil.which and absolute fallback paths.
    """
    which_path = shutil.which(binary_name)
    if which_path and Path(which_path).exists():
        return which_path

    if fallback_paths:
        for fp in fallback_paths:
            if Path(fp).exists() and os.access(fp, os.X_OK):
                return fp

    return binary_name


def compile_code_docker(
    workspace_dir: Union[str, Path],
    language: str = "cpp",
    policy: Optional[SandboxPolicy] = None,
    limits: Optional[CompileLimits] = None,
) -> CompileResult:
    """
    Compiles or syntax-checks source code inside a Docker container.
    """
    if policy is None:
        policy = DEFAULT_SANDBOX_POLICY
    if limits is None:
        limits = policy.compile_limits

    ws_path = Path(workspace_dir).resolve()
    container_name = f"judge-compile-{uuid.uuid4().hex[:12]}"
    lang = language.lower()

    docker_args = policy.to_docker_args(
        container_name=container_name,
        workspace_dir=ws_path,
        mount_read_only=False,
    )

    if lang == "python":
        compiler_cmd = [policy.runner_image, "python3", "-m", "py_compile", "/sandbox/main.py"]
        expected_target = ws_path / "main.py"
    elif lang == "java":
        compiler_cmd = [policy.runner_image, "javac", "/sandbox/Main.java"]
        expected_target = ws_path / "Main.class"
    else:  # cpp
        compiler_cmd = [policy.runner_image, "g++"] + DEFAULT_COMPILER_FLAGS + [
            "/sandbox/source.cpp",
            "-o",
            "/sandbox/main",
        ]
        expected_target = ws_path / "main"

    full_cmd = docker_args + compiler_cmd

    start_time = time.monotonic()
    timed_out = False
    stdout_str = ""
    stderr_str = ""
    error_msg: Optional[str] = None
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

        if proc.returncode == 125:
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

        oom_killed = _inspect_compile_oom_killed(container_name)

        success = (proc.returncode == 0) and expected_target.exists() and not oom_killed

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

    except Exception as ex:
        duration_ms = (time.monotonic() - start_time) * 1000.0
        tb_str = traceback.format_exc()
        logger.error(f"[compile_code_docker] Docker compilation exception: {ex}\n{tb_str}")
        print(f"[compile_code_docker ERROR] {ex}\n{tb_str}", file=sys.stderr)
        return CompileResult(
            success=False,
            stdout="",
            stderr=f"Docker compilation process error: {str(ex)}",
            duration_ms=round(duration_ms, 2),
            timed_out=False,
            oom_killed=False,
            is_docker_system_error=True,
            error_message=f"Docker compilation process error: {str(ex)}",
        )

    finally:
        _kill_and_remove_container(container_name)


def compile_cpp_docker(
    workspace_dir: Union[str, Path],
    policy: Optional[SandboxPolicy] = None,
    limits: Optional[CompileLimits] = None,
) -> CompileResult:
    """Backward-compatible C++ Docker compile helper."""
    return compile_code_docker(workspace_dir=workspace_dir, language="cpp", policy=policy, limits=limits)


def compile_code(
    source_path: Union[str, Path],
    output_path: Union[str, Path],
    language: str = "cpp",
    limits: Optional[CompileLimits] = None,
    use_docker: bool = False,
    policy: Optional[SandboxPolicy] = None,
) -> CompileResult:
    """
    Main compilation & syntax validation interface supporting C++, Python, and Java.
    Executes directly via system binaries when use_docker is False.
    """
    if use_docker:
        src_parent = Path(source_path).resolve().parent
        return compile_code_docker(workspace_dir=src_parent, language=language, policy=policy, limits=limits)

    if limits is None:
        limits = CompileLimits()

    src = Path(source_path).resolve()
    out = Path(output_path).resolve()
    cwd = src.parent
    lang = language.lower()

    if lang == "python":
        py_bin = find_executable("python3", [sys.executable, "/usr/bin/python3", "/usr/local/bin/python3"])
        cmd = [py_bin, "-m", "py_compile", str(src)]
    elif lang == "java":
        javac_bin = find_executable("javac", ["/usr/bin/javac", "/usr/local/bin/javac", "/usr/lib/jvm/default-java/bin/javac"])
        cmd = [javac_bin, str(src)]
    else:  # cpp
        cpp_bin = find_executable("g++", ["/usr/bin/g++", "/usr/local/bin/g++", "/usr/bin/gcc", "/usr/local/bin/gcc"])
        cmd = [cpp_bin] + DEFAULT_COMPILER_FLAGS + [str(src), "-o", str(out)]

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
        sanitized_stderr = stderr_str.replace(str(src), "source_file").replace(str(cwd), ".")

        success = (proc.returncode == 0) and out.exists()
        error_msg = f"Compilation failed with exit code {proc.returncode}." if not success else None

        if not success:
            logger.warning(f"[compile_code] Local compilation failed for {lang} ({cmd[0]}): exit_code={proc.returncode}\nstderr: {stderr_str}")

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

        logger.warning(f"[compile_code] Compilation timed out for {lang} after {limits.timeout_s}s")
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

    except FileNotFoundError as fnfe:
        duration_ms = (time.monotonic() - start_time) * 1000.0
        tb_str = traceback.format_exc()
        logger.error(f"[compile_code] Compiler executable '{cmd[0]}' not found: {fnfe}\n{tb_str}")
        print(f"[Compiler ERROR] Executable '{cmd[0]}' not found: {fnfe}\n{tb_str}", file=sys.stderr)
        return CompileResult(
            success=False,
            stdout="",
            stderr=f"Compiler binary for '{language}' ({cmd[0]}) not found on host system.",
            duration_ms=round(duration_ms, 2),
            timed_out=False,
            oom_killed=False,
            is_docker_system_error=False,
            error_message=f"Compiler binary for '{language}' ({cmd[0]}) not found on host system.",
        )

    except Exception as ex:
        duration_ms = (time.monotonic() - start_time) * 1000.0
        tb_str = traceback.format_exc()
        logger.error(f"[compile_code] Unexpected compilation exception for {lang}: {ex}\n{tb_str}")
        print(f"[Compiler ERROR] Exception for '{language}': {ex}\n{tb_str}", file=sys.stderr)
        return CompileResult(
            success=False,
            stdout="",
            stderr=f"Compilation process failure: {str(ex)}",
            duration_ms=round(duration_ms, 2),
            timed_out=False,
            oom_killed=False,
            is_docker_system_error=True,
            error_message=f"Compilation process failure: {str(ex)}",
        )


def compile_cpp(
    source_path: Union[str, Path],
    output_path: Union[str, Path],
    limits: Optional[CompileLimits] = None,
    use_docker: bool = False,
    policy: Optional[SandboxPolicy] = None,
) -> CompileResult:
    return compile_code(
        source_path=source_path,
        output_path=output_path,
        language="cpp",
        limits=limits,
        use_docker=use_docker,
        policy=policy,
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
